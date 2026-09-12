import asyncio
import json
import logging
import math
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from modules.llm.recommendations.types import (
    AdvisorCatalog,
    FitLevel,
    RecommendationWarning,
    ScoredModel,
    SystemProfile,
)

LOGGER = logging.getLogger(__name__)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
VERSION_PATTERN = re.compile(r"(\d+\.\d+\.\d+)")

# Bumped whenever ScoredModel changes shape. A mismatch discards the file and
# rescans: cached rows are an optimisation, never something worth migrating.
CACHE_VERSION = 1

# Every `plan` process re-detects hardware and loads the whole catalog, so
# the curated fan-out is throttled rather than spawned all at once.
PLAN_CONCURRENCY = 3

# `plan` writes TooTight; `fit`/`recommend` write "Too Tight". Both slugify to
# different codes, and an unrecognised one silently became UNKNOWN.
_FIT_ALIASES = {"tootight": FitLevel.TOO_TIGHT}

# Two subcommands, two spellings, one vocabulary. `recommend` emits
# GPU / CPU+GPU / CPU / MoE; `plan` emits Gpu / CpuOffload / CpuOnly.
_RUN_MODES = {
    "gpu": "gpu",
    "cpu_gpu": "cpu_offload",
    "cpuoffload": "cpu_offload",
    "cpu": "cpu_only",
    "cpuonly": "cpu_only",
    "moe": "moe_offload",
}

# llmfit finds an NVIDIA card by running nvidia-smi, which is not always on
# PATH: WSL keeps it under /usr/lib/wsl/lib, and desktop launchers start with a
# shorter PATH than a shell. A tool it cannot find reads as a card that is not
# there, and every model is then scored CPU-only on a machine with a GPU.
_VENDOR_TOOL_DIRS = (
    "/usr/lib/wsl/lib",
    "/usr/local/cuda/bin",
    "/opt/cuda/bin",
    r"C:\Program Files\NVIDIA Corporation\NVSMI",
)

# Tuple fields survive a JSON round-trip as lists.
_TUPLE_FIELDS = ("capability_ids", "gguf_sources", "notes")


class LlmfitError(RuntimeError):
    def __init__(self, code: str, public_message: str, detail: str = "") -> None:
        super().__init__(detail or public_message)
        self.code = code
        self.public_message = public_message


class LlmfitAdvisor:
    """Scores models with the pinned llmfit binary and caches the result.

    The cache lives here rather than in CatalogService because its fingerprint
    needs the hardware profile, and nothing above this seam should re-derive it.
    """

    def __init__(
        self,
        executable: Path,
        expected_version: str,
        timeout_seconds: float,
        curated: tuple[tuple[str, str | None], ...] = (),
        *,
        cache_path: Path | None = None,
        bulk_limit: int = 20000,
        deadline_seconds: float = 90.0,
    ) -> None:
        self._executable = executable
        self._expected_version = expected_version
        self._timeout_seconds = timeout_seconds
        self._curated = curated
        self._cache_path = cache_path
        self._bulk_limit = bulk_limit
        self._deadline_seconds = deadline_seconds
        self._plan_slots = asyncio.Semaphore(PLAN_CONCURRENCY)

    async def scan(self, max_context: int, *, refresh: bool = False) -> AdvisorCatalog:
        # Tier 1 is fatal: without a version and a hardware profile there is
        # nothing to score against and no fingerprint to key a cache on.
        try:
            version = await self._version()
            if version != self._expected_version:
                return AdvisorCatalog(
                    system=None,
                    models=(),
                    llmfit_version=version,
                    warnings=(
                        RecommendationWarning(
                            "version_mismatch",
                            "Model recommendations are unavailable until llmfit is updated.",
                        ),
                    ),
                )
            system = _parse_system(await self._json("--json", "system"))
        except LlmfitError as error:
            LOGGER.warning("llmfit probe failed (%s): %s", error.code, error)
            return AdvisorCatalog(
                system=None,
                models=(),
                llmfit_version=None,
                warnings=(RecommendationWarning(error.code, error.public_message),),
            )

        fingerprint = _fingerprint(version, system, max_context)
        if not refresh:
            cached = self._read_cache(fingerprint)
            if cached is not None:
                return AdvisorCatalog(system, cached, version)

        # Tier 2 degrades: a failure here keeps the hardware panel alive rather
        # than blanking the catalog and marking every installed model unknown.
        try:
            async with asyncio.timeout(self._deadline_seconds):
                models, warnings = await self._scan_models(system, max_context)
        except TimeoutError:
            LOGGER.warning("llmfit scan exceeded %.0fs", self._deadline_seconds)
            return AdvisorCatalog(
                system,
                (),
                version,
                (
                    RecommendationWarning(
                        "timeout", "Hardware detection took too long. Try rescanning."
                    ),
                ),
            )

        self._write_cache(fingerprint, models)
        return AdvisorCatalog(system, models, version, warnings)

    async def _scan_models(
        self, system: SystemProfile, max_context: int
    ) -> tuple[tuple[ScoredModel, ...], tuple[RecommendationWarning, ...]]:
        base = (
            "--json",
            "--max-context",
            str(max_context),
            *_ram_override(system),
        )
        outcomes = await asyncio.gather(
            self._bulk(base),
            *(
                self._plan(base, model_id, quantization, max_context)
                for model_id, quantization in self._curated
            ),
            return_exceptions=True,
        )

        warnings: list[RecommendationWarning] = []
        bulk, *planned = outcomes

        by_id: dict[str, ScoredModel] = {}
        if isinstance(bulk, BaseException):
            LOGGER.warning("llmfit bulk scan failed: %s", bulk)
            warnings.append(
                RecommendationWarning(
                    "scan_failed", "Hardware recommendations could not be calculated."
                )
            )
        else:
            for model in bulk:
                by_id.setdefault(model.canonical_id, model)
            if len(bulk) >= self._bulk_limit:
                warnings.append(
                    RecommendationWarning(
                        "catalog_truncated",
                        "Some models were left out of the compatibility scan.",
                    )
                )

        # A curated verdict always wins: it is the only one scored against the
        # quantization we actually install.
        for outcome in planned:
            if isinstance(outcome, BaseException) or outcome is None:
                continue
            by_id[outcome.canonical_id] = _merge_curated(
                by_id.get(outcome.canonical_id), outcome
            )

        return tuple(by_id.values()), tuple(warnings)

    async def _bulk(self, base: tuple[str, ...]) -> tuple[ScoredModel, ...]:
        payload = await self._json(
            *base,
            "recommend",
            "-n",
            str(self._bulk_limit),
            "--force-runtime",
            "llamacpp",
        )
        return tuple(_parse_model(row) for row in _model_rows(payload))

    async def _plan(
        self,
        base: tuple[str, ...],
        model_id: str,
        quantization: str | None,
        max_context: int,
    ) -> ScoredModel | None:
        """One curated model, scored at the quantization we install.

        A model llmfit cannot find exits 1 with empty stdout. That is a soft
        miss for this row, never a failure of the whole scan.
        """
        args = [*base, "plan", model_id, "--context", str(max_context)]
        if quantization is not None:
            args.extend(("--quant", quantization))
        async with self._plan_slots:
            try:
                output = await self._run(*args)
            except LlmfitError as error:
                LOGGER.info("llmfit could not plan %s: %s", model_id, error)
                return None
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            LOGGER.info("llmfit returned no plan for %s", model_id)
            return None
        return _parse_plan(payload, model_id, quantization)

    async def _version(self) -> str:
        output = await self._run("--version")
        match = VERSION_PATTERN.search(output)
        if match is None:
            raise LlmfitError(
                "invalid_output",
                "Model recommendations are temporarily unavailable.",
                "llmfit --version returned no semantic version",
            )
        return match.group(1)

    async def _json(self, *args: str) -> Any:
        output = await self._run(*args)
        try:
            return json.loads(output)
        except json.JSONDecodeError as error:
            raise LlmfitError(
                "invalid_output",
                "Model recommendations are temporarily unavailable.",
                f"invalid llmfit JSON: {error}",
            ) from error

    async def _run(self, *args: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                str(self._executable),
                # llmfit otherwise starts a background web dashboard, which an
                # airgapped desktop app must never expose.
                "--no-dashboard",
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=MAX_OUTPUT_BYTES,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env={**os.environ, "PATH": _tool_search_path(os.environ)},
            )
        except FileNotFoundError as error:
            raise LlmfitError(
                "missing",
                "Hardware recommendations are unavailable because llmfit is missing.",
            ) from error
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout_seconds
            )
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise LlmfitError(
                "timeout",
                "Hardware detection took too long. Try rescanning.",
            ) from error

        if len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES:
            raise LlmfitError(
                "invalid_output",
                "Model recommendations returned too much data.",
            )
        if process.returncode != 0:
            detail = stderr.decode(errors="replace").strip()
            raise LlmfitError(
                "scan_failed",
                "Hardware recommendations could not be calculated.",
                detail,
            )
        return stdout.decode().strip()

    def _read_cache(
        self, fingerprint: dict[str, Any]
    ) -> tuple[ScoredModel, ...] | None:
        """Cached rows for this exact fingerprint, or None to rescan.

        Every failure mode is "slower", never "broken": a missing, truncated,
        stale or unreadable file just means a full scan.
        """
        if self._cache_path is None:
            return None
        try:
            document = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if document.get("cache_version") != CACHE_VERSION:
                return None
            if document.get("fingerprint") != fingerprint:
                return None
            return tuple(_row_from_json(row) for row in document["models"])
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, KeyError) as error:
            LOGGER.warning("discarding unreadable llmfit cache: %s", error)
            return None

    def _write_cache(
        self, fingerprint: dict[str, Any], models: tuple[ScoredModel, ...]
    ) -> None:
        if self._cache_path is None or not models:
            return
        document = {
            "cache_version": CACHE_VERSION,
            "fingerprint": fingerprint,
            "scanned_at": datetime.now(UTC).isoformat(),
            "models": [_row_to_json(model) for model in models],
        }
        # Rename onto the final path so an interrupted multi-megabyte write
        # cannot leave JSON that parses as garbage.
        temporary = self._cache_path.with_suffix(".json.tmp")
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(document), encoding="utf-8")
            os.replace(temporary, self._cache_path)
        except OSError as error:
            LOGGER.warning("could not write llmfit cache: %s", error)
            temporary.unlink(missing_ok=True)


def _tool_search_path(
    environ: Mapping[str, str], candidates: tuple[str, ...] | None = None
) -> str:
    """PATH with the directories vendor tools hide in appended.

    Appended rather than prepended so a tool the user already has on PATH
    wins, and only for directories that exist, so this is inert on machines
    that do not need it.
    """
    current = environ.get("PATH", "")
    present = current.split(os.pathsep)
    extra = [
        directory
        for directory in (_VENDOR_TOOL_DIRS if candidates is None else candidates)
        if directory not in present and Path(directory).is_dir()
    ]
    if not extra:
        return current
    return os.pathsep.join([part for part in (current, *extra) if part])


def _ram_override(system: SystemProfile) -> tuple[str, ...]:
    """Score against total RAM so a verdict describes the machine, not the hour.

    Free RAM drifts with whatever else is open, and scoring against it makes
    models appear and disappear between scans on unchanged hardware.
    """
    total = system.total_ram_gb
    if not total or total <= 0:
        return ()
    return ("--ram", f"{math.floor(total)}G")


def _fingerprint(
    version: str, system: SystemProfile, max_context: int
) -> dict[str, Any]:
    """The inputs llmfit was given. Stored as fields, not a hash, so that an
    unexpected invalidation can be read straight out of the cache file."""
    return {
        "llmfit_version": version,
        "gpu_name": system.gpu_name,
        "gpu_vram_gb": system.gpu_vram_gb,
        "gpu_count": system.gpu_count,
        "total_ram_gb": system.total_ram_gb,
        "cpu_name": system.cpu_name,
        "cpu_cores": system.cpu_cores,
        "backend": system.backend,
        "max_context": max_context,
    }


def _merge_curated(base: ScoredModel | None, verdict: ScoredModel) -> ScoredModel:
    """Metadata from the bulk row, verdict from `plan`.

    `plan` knows the artifact we install but not its catalog metadata; the bulk
    row knows the metadata but scores a quantization we may never pull.
    """
    if base is None:
        return verdict
    return replace(
        base,
        fit=verdict.fit,
        run_mode=verdict.run_mode,
        estimated_tps=verdict.estimated_tps,
        memory_required_gb=verdict.memory_required_gb,
    )


def _code(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _fit_level(value: Any) -> FitLevel:
    code = _code(value)
    if code is None:
        return FitLevel.UNKNOWN
    try:
        return FitLevel(code)
    except ValueError:
        return _FIT_ALIASES.get(code, FitLevel.UNKNOWN)


def _run_mode(value: Any) -> str | None:
    code = _code(value)
    if code is None:
        return None
    return _RUN_MODES.get(code, code)


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _parse_system(payload: Any) -> SystemProfile:
    if not isinstance(payload, dict) or not isinstance(payload.get("system"), dict):
        raise LlmfitError(
            "invalid_output",
            "Hardware recommendations returned an unsupported system profile.",
        )
    row = payload["system"]
    return SystemProfile(
        cpu_name=_text(row.get("cpu_name")),
        cpu_cores=_integer(row.get("cpu_cores")),
        total_ram_gb=_number(row.get("total_ram_gb")),
        available_ram_gb=_number(row.get("available_ram_gb")),
        has_gpu=bool(row.get("has_gpu", False)),
        gpu_name=_text(row.get("gpu_name")),
        gpu_vram_gb=_number(row.get("gpu_vram_gb")),
        gpu_count=_integer(row.get("gpu_count")) or 0,
        backend=_text(row.get("backend")),
        unified_memory=bool(row.get("unified_memory", False)),
    )


def _model_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise LlmfitError(
            "invalid_output",
            "Model recommendations returned an unsupported catalog.",
        )
    if not all(isinstance(row, dict) for row in payload["models"]):
        raise LlmfitError(
            "invalid_output",
            "Model recommendations contained an invalid model entry.",
        )
    return payload["models"]


def _parse_model(row: dict[str, Any]) -> ScoredModel:
    name = row.get("name")
    if not isinstance(name, str) or not name.strip():
        raise LlmfitError(
            "invalid_output",
            "Model recommendations contained a model without an id.",
        )
    display = name.rsplit("/", 1)[-1]
    capabilities = row.get("capability_ids", row.get("capabilities", []))
    notes = row.get("notes", [])
    gguf_sources = row.get("gguf_sources", [])

    return ScoredModel(
        canonical_id=name,
        publisher=_text(row.get("provider")),
        family=display.split("-", 1)[0] or display,
        display_name=display,
        parameter_count=_text(row.get("parameter_count")),
        use_case=_code(row.get("use_case") or row.get("category")),
        fit=_fit_level(row.get("fit_level")),
        score=_number(row.get("score")),
        runtime=_code(row.get("runtime")),
        run_mode=_run_mode(row.get("run_mode")),
        best_quant=_text(row.get("best_quant")),
        memory_required_gb=_number(row.get("memory_required_gb")),
        disk_size_gb=_number(row.get("disk_size_gb")),
        estimated_tps=_number(row.get("estimated_tps")),
        prefill_tps=_number(row.get("prefill_tps")),
        ttft_ms=_number(row.get("ttft_ms")),
        estimate_confidence=_code(row.get("estimate_confidence")),
        effective_context_length=_integer(row.get("effective_context_length")),
        capability_ids=(
            tuple(code for item in capabilities if (code := _code(item)))
            if isinstance(capabilities, list)
            else ()
        ),
        license=_text(row.get("license")),
        ollama_name=_text(row.get("ollama_name")),
        gguf_sources=(
            tuple(item for item in gguf_sources if isinstance(item, str))
            if isinstance(gguf_sources, list)
            else ()
        ),
        notes=(
            tuple(item for item in notes if isinstance(item, str))
            if isinstance(notes, list)
            else ()
        ),
    )


def _parse_plan(
    payload: Any, model_id: str, quantization: str | None
) -> ScoredModel | None:
    """A `plan` verdict for one model. Shape differs from `fit`/`recommend`:
    the fit lives under `current`, and the requirement under `minimum`."""
    if not isinstance(payload, dict):
        return None
    current = payload.get("current")
    if not isinstance(current, dict):
        return None
    name = _text(payload.get("model_name")) or model_id
    display = name.rsplit("/", 1)[-1]
    minimum = payload.get("minimum")
    required = _number(minimum.get("vram_gb")) if isinstance(minimum, dict) else None

    return ScoredModel(
        canonical_id=name,
        publisher=_text(payload.get("provider")),
        family=display.split("-", 1)[0] or display,
        display_name=display,
        parameter_count=None,
        use_case=None,
        fit=_fit_level(current.get("fit_level")),
        score=None,
        runtime=None,
        run_mode=_run_mode(current.get("run_mode")),
        best_quant=quantization,
        memory_required_gb=required,
        disk_size_gb=None,
        estimated_tps=_number(current.get("estimated_tps")),
        prefill_tps=None,
        ttft_ms=None,
        estimate_confidence=None,
        effective_context_length=_integer(payload.get("context")),
        capability_ids=(),
        license=None,
        ollama_name=None,
        gguf_sources=(),
    )


def _row_to_json(model: ScoredModel) -> dict[str, Any]:
    row = asdict(model)
    row["fit"] = model.fit.value
    return row


def _row_from_json(row: dict[str, Any]) -> ScoredModel:
    values = dict(row)
    values["fit"] = FitLevel(values["fit"])
    for field in _TUPLE_FIELDS:
        values[field] = tuple(values.get(field) or ())
    return ScoredModel(**values)
