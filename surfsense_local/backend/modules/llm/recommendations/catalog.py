import asyncio
import logging
import secrets
import shutil
from dataclasses import replace
from pathlib import Path

from modules.llm.recommendations.curated_models import (
    CuratedModel,
    CuratedModelsManifest,
)
from modules.llm.recommendations.protocols import LocalRuntime, ModelAdvisor
from modules.llm.recommendations.types import (
    AdvisorCatalog,
    CatalogResult,
    CatalogRow,
    FitLevel,
    InstalledModel,
    InstallPlan,
    RecommendationWarning,
    ScoredModel,
)

FIT_ORDER = {
    FitLevel.PERFECT: 0,
    FitLevel.GOOD: 1,
    FitLevel.MARGINAL: 2,
    FitLevel.TOO_TIGHT: 3,
    FitLevel.UNKNOWN: 4,
}
LOGGER = logging.getLogger(__name__)


class UnknownCatalogIdError(ValueError):
    pass


class RuntimeBusyError(RuntimeError):
    pass


class InsufficientDiskError(RuntimeError):
    def __init__(self, required: int, available: int) -> None:
        super().__init__("insufficient disk space")
        self.required = required
        self.available = available


class CatalogService:
    def __init__(
        self,
        advisor: ModelAdvisor,
        runtimes: list[LocalRuntime],
        curated_models: CuratedModelsManifest,
        *,
        max_context: int,
        runtime_storage: dict[str, Path] | None = None,
        initial_warnings: tuple[RecommendationWarning, ...] = (),
    ) -> None:
        self._advisor = advisor
        self._runtimes = {runtime.name: runtime for runtime in runtimes}
        self._curated_models = {
            model.model_id: model for model in curated_models.models
        }
        self._max_context = max_context
        self._runtime_storage = runtime_storage or {}
        self._initial_warnings = initial_warnings
        self._scan: AdvisorCatalog | None = None
        self._scan_lock = asyncio.Lock()
        self._ids: dict[tuple[str, str], str] = {}
        self._plans: dict[str, tuple[LocalRuntime, ScoredModel, InstallPlan]] = {}
        self._logged_collision_keys: set[tuple[str, str]] = set()
        self._install_locks = {runtime.name: asyncio.Lock() for runtime in runtimes}

    async def advisor_catalog(self, *, refresh: bool = False) -> AdvisorCatalog:
        async with self._scan_lock:
            if refresh:
                self._scan = None
                self._ids.clear()
                self._plans.clear()
                self._logged_collision_keys.clear()
            if self._scan is None:
                self._scan = await self._advisor.scan(
                    self._max_context, refresh=refresh
                )
            return self._scan

    async def catalog(
        self,
        *,
        selected: tuple[str, str] | None,
        refresh: bool = False,
    ) -> CatalogResult:
        scan = await self.advisor_catalog(refresh=refresh)
        health_results = await asyncio.gather(
            *(runtime.health() for runtime in self._runtimes.values()),
            return_exceptions=True,
        )
        runtime_status = dict(
            zip(
                self._runtimes,
                (
                    result if isinstance(result, bool) else False
                    for result in health_results
                ),
                strict=True,
            )
        )
        inventories = await asyncio.gather(
            *(runtime.installed_models() for runtime in self._runtimes.values()),
            return_exceptions=True,
        )
        installed_by_key: dict[tuple[str, str], InstalledModel] = {}
        warnings = [*self._initial_warnings, *scan.warnings]
        warnings.extend(
            RecommendationWarning(
                "runtime_health_failed",
                f"Could not check {name}.",
            )
            for name, result in zip(self._runtimes, health_results, strict=True)
            if isinstance(result, BaseException)
        )
        for (runtime_name, _runtime), inventory in zip(
            self._runtimes.items(), inventories, strict=True
        ):
            if isinstance(inventory, BaseException):
                warnings.append(
                    RecommendationWarning(
                        "runtime_inventory_failed",
                        f"Could not read installed models from {runtime_name}.",
                    )
                )
                continue
            installed_by_key.update(
                {(model.runtime, model.model_name): model for model in inventory}
            )

        recommended: list[CatalogRow] = []
        explore: list[CatalogRow] = []
        installed: list[CatalogRow] = []
        matched_installed: set[tuple[str, str]] = set()
        rendered_curated: set[str] = set()
        resolved_by_key: dict[
            tuple[str, str],
            tuple[LocalRuntime, ScoredModel, InstallPlan, CuratedModel | None],
        ] = {}
        ambiguous_keys: set[tuple[str, str]] = set()
        collisions_by_key: dict[
            tuple[str, str],
            list[tuple[LocalRuntime, ScoredModel, InstallPlan, CuratedModel | None]],
        ] = {}
        self._plans.clear()

        for raw_model in scan.models:
            if _is_embedding(raw_model):
                continue
            model, curated_model = self._apply_curated_model(raw_model)
            resolved = await self._resolve(model)
            if resolved is None:
                continue
            runtime, plan = resolved
            key = (runtime.name, plan.model_name)
            candidate = (runtime, model, plan, curated_model)
            existing = resolved_by_key.get(key)
            if existing is not None and existing[1].canonical_id != model.canonical_id:
                collisions_by_key.setdefault(key, [existing]).append(candidate)
            elif key in collisions_by_key and all(
                item[1].canonical_id != model.canonical_id
                for item in collisions_by_key[key]
            ):
                collisions_by_key[key].append(candidate)
            if curated_model is not None:
                if existing is not None and existing[3] is not None:
                    if existing[1].canonical_id == model.canonical_id:
                        continue
                    resolved_by_key.pop(key)
                    ambiguous_keys.add(key)
                    continue
                ambiguous_keys.discard(key)
                resolved_by_key[key] = candidate
                continue
            if key in ambiguous_keys or (
                existing is not None and existing[3] is not None
            ):
                continue
            if existing is None:
                resolved_by_key[key] = candidate
                continue
            if existing[1].canonical_id != model.canonical_id:
                resolved_by_key.pop(key)
                ambiguous_keys.add(key)

        for key in tuple(ambiguous_keys):
            candidates = collisions_by_key[key]
            if any(candidate[3] is not None for candidate in candidates):
                continue
            runtime = candidates[0][0]
            model = _runtime_target_model(key, candidates)
            plan = await runtime.resolve(model)
            if plan is None or (plan.runtime, plan.model_name) != key:
                continue
            resolved_by_key[key] = (runtime, model, plan, None)
            ambiguous_keys.remove(key)

        for key, candidates in collisions_by_key.items():
            if key in self._logged_collision_keys:
                continue
            self._logged_collision_keys.add(key)
            canonical_ids = {candidate[1].canonical_id for candidate in candidates}
            resolved = resolved_by_key.get(key)
            if key in ambiguous_keys or resolved is None:
                LOGGER.warning(
                    "Hiding ambiguous models %s for target %s:%s",
                    ", ".join(sorted(canonical_ids)),
                    *key,
                )
            elif resolved[3] is not None:
                LOGGER.warning(
                    "Keeping curated model %s over %s for target %s:%s",
                    resolved[1].canonical_id,
                    ", ".join(sorted(canonical_ids - {resolved[1].canonical_id})),
                    *key,
                )
            else:
                LOGGER.warning(
                    "Representing ambiguous models %s as runtime target %s:%s",
                    ", ".join(sorted(canonical_ids)),
                    *key,
                )

        for key, (runtime, model, plan, curated_model) in resolved_by_key.items():
            is_installed = key in installed_by_key
            row = self._row(
                model,
                plan,
                installed=is_installed,
                selected=selected == key,
                can_install=runtime_status.get(runtime.name, False),
                curated_model=curated_model,
            )
            self._plans[row.catalog_id] = (runtime, model, plan)
            if curated_model is not None:
                rendered_curated.add(curated_model.model_id)
            if is_installed:
                installed.append(row)
                matched_installed.add(key)
            elif curated_model is not None:
                # Team-tested models are always listed, even when they do not
                # fit: a disabled row explains itself, an absent one does not.
                recommended.append(row)
            elif model.fit in {
                FitLevel.PERFECT,
                FitLevel.GOOD,
                FitLevel.MARGINAL,
            }:
                explore.append(row)

        # A curated model llmfit could not score at all still gets a row, built
        # from the manifest. Routed through _resolve/_row so it registers in
        # self._plans; a hand-built CatalogRow would fail preflight on click.
        for model_id, curated_model in self._curated_models.items():
            if model_id in rendered_curated:
                continue
            placeholder = _curated_placeholder(model_id, curated_model)
            resolved = await self._resolve(placeholder)
            if resolved is None:
                continue
            runtime, plan = resolved
            key = (runtime.name, plan.model_name)
            if key in resolved_by_key or key in installed_by_key:
                continue
            row = self._row(
                placeholder,
                plan,
                installed=False,
                selected=selected == key,
                can_install=runtime_status.get(runtime.name, False),
                curated_model=curated_model,
            )
            self._plans[row.catalog_id] = (runtime, placeholder, plan)
            recommended.append(row)

        for key, local_model in installed_by_key.items():
            if key in matched_installed or "completion" not in local_model.capabilities:
                continue
            catalog_id = self._id(f"{key[0]}:{key[1]}", key[0])
            installed.append(
                CatalogRow(
                    catalog_id=catalog_id,
                    canonical_id=f"{key[0]}:{key[1]}",
                    family=key[1].split(":", 1)[0],
                    label=key[1],
                    publisher=None,
                    parameter_count=None,
                    fit=FitLevel.UNKNOWN,
                    score=None,
                    memory_required_gb=None,
                    disk_size_gb=None,
                    estimated_tps=None,
                    prefill_tps=None,
                    ttft_ms=None,
                    effective_context_length=None,
                    estimate_confidence=None,
                    license=None,
                    runtime=key[0],
                    runtime_model=key[1],
                    quantization=local_model.quantization,
                    installed=True,
                    selected=selected == key,
                    can_install=False,
                    can_delete=True,
                    warnings=("No current llmfit estimate is available.",),
                )
            )

        return CatalogResult(
            hardware=scan.system,
            llmfit_version=scan.llmfit_version,
            recommended=tuple(sorted(recommended, key=_sort_key)),
            explore=tuple(sorted(explore, key=_sort_key)),
            installed=tuple(sorted(installed, key=_sort_key)),
            warnings=tuple(warnings),
            runtime_status=runtime_status,
        )

    async def preflight(
        self, catalog_id: str
    ) -> tuple[LocalRuntime, ScoredModel, InstallPlan]:
        found = self._plans.get(catalog_id)
        if found is None:
            raise UnknownCatalogIdError(catalog_id)
        runtime, model, old_plan = found
        plan = await runtime.resolve(model)
        if plan is None or plan != old_plan:
            raise UnknownCatalogIdError(catalog_id)
        if not await runtime.health():
            raise RuntimeError(f"{runtime.name} is unavailable")
        storage = self._runtime_storage.get(runtime.name)
        if storage is not None and plan.expected_bytes is not None:
            available = shutil.disk_usage(storage).free
            if available < plan.expected_bytes:
                raise InsufficientDiskError(plan.expected_bytes, available)
        return runtime, model, plan

    def install_lock(self, runtime: str) -> asyncio.Lock:
        return self._install_locks[runtime]

    def _apply_curated_model(
        self, model: ScoredModel
    ) -> tuple[ScoredModel, CuratedModel | None]:
        curated_model = self._curated_models.get(model.canonical_id)
        if curated_model is None:
            return model, None
        ollama = curated_model.artifacts.ollama
        return (
            replace(
                model,
                family=curated_model.family,
                ollama_name=ollama.name if ollama is not None else model.ollama_name,
                ollama_quantization=(
                    ollama.quantization if ollama is not None else None
                ),
            ),
            curated_model,
        )

    async def _resolve(
        self, model: ScoredModel
    ) -> tuple[LocalRuntime, InstallPlan] | None:
        for runtime in self._runtimes.values():
            plan = await runtime.resolve(model)
            if plan is not None:
                return runtime, plan
        return None

    def _row(
        self,
        model: ScoredModel,
        plan: InstallPlan,
        *,
        installed: bool,
        selected: bool,
        can_install: bool,
        curated_model: CuratedModel | None = None,
    ) -> CatalogRow:
        warnings = list(model.notes)
        if model.fit is FitLevel.MARGINAL:
            warnings.append("This model may be slow or fail at long context.")
        if model.fit is FitLevel.TOO_TIGHT:
            warnings.append("This model is too large for the available memory.")
        if model.fit is FitLevel.UNKNOWN:
            warnings.append("No current llmfit estimate is available.")
        # Chat pins num_ctx to the scored context, so a model that cannot reach
        # it would be installed and then behave badly.
        short_context = (
            curated_model is not None
            and (model.effective_context_length or 0) < curated_model.minimum_context
        )
        if short_context:
            warnings.append(
                "This model runs with a shorter context than SurfSense needs."
            )
        return CatalogRow(
            catalog_id=self._id(model.canonical_id, plan.runtime),
            canonical_id=model.canonical_id,
            family=model.family,
            label=model.display_name,
            publisher=model.publisher,
            parameter_count=model.parameter_count,
            fit=model.fit,
            score=model.score,
            memory_required_gb=model.memory_required_gb,
            disk_size_gb=model.disk_size_gb,
            estimated_tps=model.estimated_tps,
            prefill_tps=model.prefill_tps,
            ttft_ms=model.ttft_ms,
            effective_context_length=model.effective_context_length,
            estimate_confidence=model.estimate_confidence,
            license=model.license,
            runtime=plan.runtime,
            runtime_model=plan.model_name,
            quantization=plan.quantization,
            installed=installed,
            selected=selected,
            can_install=(
                can_install
                and model.fit is not FitLevel.TOO_TIGHT
                and not short_context
            ),
            can_delete=installed,
            warnings=tuple(warnings),
        )

    def _id(self, canonical_id: str, runtime: str) -> str:
        key = (canonical_id, runtime)
        if key not in self._ids:
            self._ids[key] = secrets.token_urlsafe(18)
        return self._ids[key]


def _runtime_target_model(
    key: tuple[str, str],
    candidates: list[
        tuple[LocalRuntime, ScoredModel, InstallPlan, CuratedModel | None]
    ],
) -> ScoredModel:
    source = max(
        (candidate[1] for candidate in candidates),
        key=lambda model: (
            FIT_ORDER[model.fit],
            model.memory_required_gb or 0,
            model.canonical_id,
        ),
    )
    runtime, runtime_model = key
    return replace(
        source,
        canonical_id=f"{runtime}:{runtime_model}",
        family=runtime_model.split(":", 1)[0],
        display_name=runtime_model,
        publisher=None,
        parameter_count=None,
        use_case=None,
        score=None,
        capability_ids=(),
        license=None,
        notes=(
            *source.notes,
            "Multiple catalog entries map to this exact runtime model.",
        ),
        ollama_name=runtime_model if runtime == "ollama" else None,
    )


def _curated_placeholder(model_id: str, curated_model: CuratedModel) -> ScoredModel:
    """A curated model as the manifest alone describes it.

    fit is UNKNOWN rather than a guess, but the row stays installable: these
    are hand-vetted configurations and onboarding depends on them.
    """
    ollama = curated_model.artifacts.ollama
    display = model_id.rsplit("/", 1)[-1]
    return ScoredModel(
        canonical_id=model_id,
        publisher=None,
        family=curated_model.family,
        display_name=display,
        parameter_count=None,
        use_case=None,
        fit=FitLevel.UNKNOWN,
        score=None,
        runtime=None,
        run_mode=None,
        best_quant=None,
        memory_required_gb=None,
        disk_size_gb=None,
        estimated_tps=None,
        prefill_tps=None,
        ttft_ms=None,
        estimate_confidence=None,
        effective_context_length=curated_model.minimum_context,
        capability_ids=(),
        license=None,
        ollama_name=None if ollama is None else ollama.name,
        gguf_sources=(),
        ollama_quantization=None if ollama is None else ollama.quantization,
    )


def _is_embedding(model: ScoredModel) -> bool:
    return (model.use_case is not None and "embedding" in model.use_case) or (
        bool(model.capability_ids)
        and set(model.capability_ids).issubset({"embedding", "embeddings"})
    )


def _sort_key(row: CatalogRow) -> tuple[int, float, str]:
    return (FIT_ORDER[row.fit], -(row.score or 0), row.canonical_id)
