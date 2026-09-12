import json
import os
from pathlib import Path

import pytest

from modules.llm.recommendations.llmfit import (
    LlmfitAdvisor,
    _fit_level,
    _ram_override,
    _run_mode,
    _tool_search_path,
)
from modules.llm.recommendations.types import FitLevel, SystemProfile

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parents[3] / "fixtures" / "llmfit"


def _executable(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "llmfit"
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)
    return path


def _stub(tmp_path: Path, *, plan: str | None = None) -> Path:
    """A fake llmfit that dispatches on subcommand, as the real one does."""
    system = json.dumps(json.loads((FIXTURES / "system.json").read_text()))
    recommend = json.dumps(json.loads((FIXTURES / "recommend.json").read_text()))
    plan_body = (
        f"print({plan!r})"
        if plan is not None
        # A model llmfit cannot find: rc=1, nothing on stdout.
        else "sys.exit(1)"
    )
    return _executable(
        tmp_path,
        f"""
import sys
if "--version" in sys.argv:
    print("llmfit 1.1.11")
elif "system" in sys.argv:
    print({system!r})
elif "recommend" in sys.argv:
    print({recommend!r})
elif "plan" in sys.argv:
    {plan_body}
else:
    print("unexpected subcommand: " + " ".join(sys.argv), file=sys.stderr)
    sys.exit(2)
""",
    )


async def test_adapter_normalizes_the_pinned_cli_contract(tmp_path: Path) -> None:
    """CLI labels, null estimates, and future fields normalize at one seam."""
    result = await LlmfitAdvisor(_stub(tmp_path), "1.1.11", 2).scan(8192)

    assert result.warnings == ()
    assert result.system is not None
    assert result.system.unified_memory is True
    assert [model.fit for model in result.models] == [
        FitLevel.GOOD,
        FitLevel.PERFECT,
    ]
    assert result.models[0].publisher == "Qwen"
    assert result.models[0].prefill_tps is None
    assert result.models[0].capability_ids == ("tool_use",)


async def test_curated_verdict_overrides_the_bulk_row(tmp_path: Path) -> None:
    """`plan` scores the quantization we install, so its verdict wins."""
    plan = (FIXTURES / "plan.json").read_text()
    advisor = LlmfitAdvisor(
        _stub(tmp_path, plan=plan),
        "1.1.11",
        2,
        (("Qwen/Qwen3-32B", "Q4_K_M"),),
    )

    result = await advisor.scan(8192)

    scored = {model.canonical_id: model for model in result.models}
    # "TooTight" (no space) is the spelling that used to fall through.
    assert scored["Qwen/Qwen3-32B"].fit is FitLevel.TOO_TIGHT
    assert scored["Qwen/Qwen3-32B"].run_mode == "gpu"
    assert result.warnings == ()


async def test_an_unplannable_curated_model_degrades_only_itself(
    tmp_path: Path,
) -> None:
    """`plan` exits 1 with empty stdout for an unknown id; the scan survives."""
    advisor = LlmfitAdvisor(
        _stub(tmp_path), "1.1.11", 2, (("NotAReal/Model", "Q4_K_M"),)
    )

    result = await advisor.scan(8192)

    assert result.warnings == ()
    assert len(result.models) == 2


async def test_a_failed_bulk_scan_keeps_the_hardware_profile(
    tmp_path: Path,
) -> None:
    """Losing the catalog must not blank the hardware panel as well."""
    system = json.dumps(json.loads((FIXTURES / "system.json").read_text()))
    executable = _executable(
        tmp_path,
        f"""
import sys
if "--version" in sys.argv:
    print("llmfit 1.1.11")
elif "system" in sys.argv:
    print({system!r})
else:
    sys.exit(2)
""",
    )

    result = await LlmfitAdvisor(executable, "1.1.11", 2).scan(8192)

    assert result.system is not None
    assert result.models == ()
    assert result.warnings[0].code == "scan_failed"


async def test_missing_binary_degrades_to_a_warning(tmp_path: Path) -> None:
    """A missing optional advisor cannot prevent the API from starting."""
    result = await LlmfitAdvisor(tmp_path / "missing", "1.1.11", 1).scan(8192)

    assert result.models == ()
    assert result.warnings[0].code == "missing"


async def test_version_drift_refuses_to_parse_unknown_output(tmp_path: Path) -> None:
    """A binary upgrade requires fixture review before recommendations resume."""
    executable = _executable(tmp_path, 'print("llmfit 2.0.0")\n')

    result = await LlmfitAdvisor(executable, "1.1.11", 1).scan(8192)

    assert result.models == ()
    assert result.warnings[0].code == "version_mismatch"


async def test_timeout_kills_the_process(tmp_path: Path) -> None:
    """A hung hardware probe returns promptly instead of leaking a child."""
    executable = _executable(tmp_path, "import time\ntime.sleep(10)\n")

    result = await LlmfitAdvisor(executable, "1.1.11", 0.01).scan(8192)

    assert result.warnings[0].code == "timeout"


async def test_malformed_json_is_not_partially_accepted(tmp_path: Path) -> None:
    """Malformed advisor output returns no recommendations."""
    executable = _executable(
        tmp_path,
        """
import sys
print("llmfit 1.1.11" if "--version" in sys.argv else "{not-json")
""",
    )

    result = await LlmfitAdvisor(executable, "1.1.11", 2).scan(8192)

    assert result.models == ()
    assert result.warnings[0].code == "invalid_output"


async def test_nonzero_exit_is_a_scan_warning(tmp_path: Path) -> None:
    """Advisor diagnostics stay in logs while the public API gets a safe warning."""
    executable = _executable(
        tmp_path,
        'import sys\nprint("probe failed", file=sys.stderr)\nsys.exit(2)\n',
    )

    result = await LlmfitAdvisor(executable, "1.1.11", 1).scan(8192)

    assert result.models == ()
    assert result.warnings[0].code == "scan_failed"


# --- pure seams: no subprocess, no disk -------------------------------------


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Too Tight", FitLevel.TOO_TIGHT),
        ("TooTight", FitLevel.TOO_TIGHT),
        ("too_tight", FitLevel.TOO_TIGHT),
        ("Perfect", FitLevel.PERFECT),
        ("nonsense", FitLevel.UNKNOWN),
        (None, FitLevel.UNKNOWN),
    ],
)
def test_fit_levels_normalize_across_subcommands(label, expected) -> None:
    """`plan` and `recommend` spell the same verdict differently."""
    assert _fit_level(label) is expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("GPU", "gpu"),
        ("Gpu", "gpu"),
        ("CPU+GPU", "cpu_offload"),
        ("CpuOffload", "cpu_offload"),
        ("CPU", "cpu_only"),
        ("CpuOnly", "cpu_only"),
        ("MoE", "moe_offload"),
        (None, None),
    ],
)
def test_run_modes_normalize_across_subcommands(label, expected) -> None:
    """MoE is a fourth mode; plan and recommend spell the other three apart."""
    assert _run_mode(label) == expected


def test_ram_override_describes_the_machine_not_the_moment() -> None:
    """Total RAM, never free: free RAM drifts and flips verdicts between scans."""
    system = SystemProfile(total_ram_gb=31.14, available_ram_gb=11.53)

    assert _ram_override(system) == ("--ram", "31G")


def test_ram_override_is_omitted_when_unknown() -> None:
    """Undetectable RAM means let llmfit self-detect, never guess a budget."""
    assert _ram_override(SystemProfile()) == ()


def test_vendor_tool_directories_are_added_when_they_exist(tmp_path: Path) -> None:
    """WSL hides nvidia-smi off PATH, and llmfit then reports no GPU at all."""
    vendor = tmp_path / "wsl-lib"
    vendor.mkdir()

    result = _tool_search_path({"PATH": "/usr/bin"}, (str(vendor),))

    assert result == f"/usr/bin{os.pathsep}{vendor}"


def test_a_directory_that_does_not_exist_is_never_added() -> None:
    """Most machines have none of these; the search path must be untouched."""
    assert _tool_search_path({"PATH": "/usr/bin"}, ("/nope/missing",)) == "/usr/bin"


def test_the_users_own_path_wins(tmp_path: Path) -> None:
    """Appended, not prepended: a tool already on PATH keeps priority."""
    vendor = tmp_path / "cuda"
    vendor.mkdir()

    result = _tool_search_path(
        {"PATH": f"/usr/bin{os.pathsep}{vendor}"}, (str(vendor),)
    )

    # Already present, so not duplicated and not moved ahead of /usr/bin.
    assert result == f"/usr/bin{os.pathsep}{vendor}"


def test_an_empty_path_does_not_gain_a_stray_separator(tmp_path: Path) -> None:
    """An empty PATH must not become a leading separator, which means cwd."""
    vendor = tmp_path / "cuda"
    vendor.mkdir()

    assert _tool_search_path({}, (str(vendor),)) == str(vendor)


async def test_the_subprocess_inherits_the_widened_search_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The widened PATH is useless unless llmfit itself is launched with it."""
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    monkeypatch.setattr(
        "modules.llm.recommendations.llmfit._VENDOR_TOOL_DIRS", (str(vendor),)
    )
    seen = tmp_path / "path.txt"
    executable = _executable(
        tmp_path,
        f"""
import os, sys
if "--version" in sys.argv:
    open({str(seen)!r}, "w").write(os.environ.get("PATH", ""))
    print("llmfit 1.1.11")
else:
    sys.exit(1)
""",
    )

    await LlmfitAdvisor(executable, "1.1.11", 5).scan(8192)

    assert str(vendor) in seen.read_text()
