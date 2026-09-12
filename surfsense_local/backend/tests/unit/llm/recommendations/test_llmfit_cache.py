import json
from pathlib import Path

import pytest

from modules.llm.recommendations.llmfit import CACHE_VERSION, LlmfitAdvisor
from modules.llm.recommendations.types import FitLevel

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parents[3] / "fixtures" / "llmfit"


def _counting_stub(tmp_path: Path) -> tuple[Path, Path]:
    """A fake llmfit that records every subcommand it is asked to run."""
    system = json.dumps(json.loads((FIXTURES / "system.json").read_text()))
    recommend = json.dumps(json.loads((FIXTURES / "recommend.json").read_text()))
    log = tmp_path / "calls.log"
    path = tmp_path / "llmfit"
    path.write_text(
        "#!/usr/bin/env python3\n"
        f"""
import sys
with open({str(log)!r}, "a") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\\n")
if "--version" in sys.argv:
    print("llmfit 1.1.11")
elif "system" in sys.argv:
    print({system!r})
elif "recommend" in sys.argv:
    print({recommend!r})
else:
    sys.exit(1)
"""
    )
    path.chmod(0o755)
    return path, log


def _advisor(executable: Path, cache: Path) -> LlmfitAdvisor:
    return LlmfitAdvisor(executable, "1.1.11", 5, cache_path=cache)


def _calls(log: Path, subcommand: str) -> int:
    if not log.exists():
        return 0
    return sum(1 for line in log.read_text().splitlines() if subcommand in line)


async def test_a_matching_fingerprint_skips_the_expensive_scan(
    tmp_path: Path,
) -> None:
    """The bulk scan dominates a cold run; unchanged hardware reuses it."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"

    first = await _advisor(executable, cache).scan(8192)
    second = await _advisor(executable, cache).scan(8192)

    assert _calls(log, "recommend") == 1
    assert [m.canonical_id for m in second.models] == [
        m.canonical_id for m in first.models
    ]
    assert second.models[0].fit is first.models[0].fit


async def test_a_new_llmfit_version_rescans_without_being_asked(
    tmp_path: Path,
) -> None:
    """An app update ships a new catalog; cached rows would hide it forever."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    await _advisor(executable, cache).scan(8192)

    document = json.loads(cache.read_text())
    document["fingerprint"]["llmfit_version"] = "1.1.10"
    cache.write_text(json.dumps(document))

    await _advisor(executable, cache).scan(8192)

    assert _calls(log, "recommend") == 2


async def test_changed_hardware_rescans_without_being_asked(
    tmp_path: Path,
) -> None:
    """New RAM or a new card invalidates the fingerprint, not a timer."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    await _advisor(executable, cache).scan(8192)

    document = json.loads(cache.read_text())
    document["fingerprint"]["total_ram_gb"] = 8.0
    cache.write_text(json.dumps(document))

    await _advisor(executable, cache).scan(8192)

    assert _calls(log, "recommend") == 2


async def test_a_changed_context_rescans(tmp_path: Path) -> None:
    """Context is an input to the score, so it belongs in the fingerprint."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"

    await _advisor(executable, cache).scan(8192)
    await _advisor(executable, cache).scan(4096)

    assert _calls(log, "recommend") == 2


async def test_an_old_cache_format_is_discarded_not_migrated(
    tmp_path: Path,
) -> None:
    """Cached rows are an optimisation; a shape change rescans, never migrates."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    await _advisor(executable, cache).scan(8192)

    document = json.loads(cache.read_text())
    document["cache_version"] = CACHE_VERSION + 1
    cache.write_text(json.dumps(document))

    await _advisor(executable, cache).scan(8192)

    assert _calls(log, "recommend") == 2
    assert json.loads(cache.read_text())["cache_version"] == CACHE_VERSION


async def test_a_corrupt_cache_is_slower_never_broken(tmp_path: Path) -> None:
    """An interrupted write must degrade to a rescan, not an error."""
    executable, _ = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    cache.write_text('{"cache_version": 1, "fingerprint": {"tr')

    result = await _advisor(executable, cache).scan(8192)

    assert result.warnings == ()
    assert len(result.models) == 2


async def test_refresh_rescans_even_when_the_fingerprint_matches(
    tmp_path: Path,
) -> None:
    """The Rescan button is the one path that ignores the cache entirely."""
    executable, log = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    await _advisor(executable, cache).scan(8192)

    await _advisor(executable, cache).scan(8192, refresh=True)

    assert _calls(log, "recommend") == 2


async def test_a_failed_scan_leaves_the_previous_cache_intact(
    tmp_path: Path,
) -> None:
    """A broken rescan must not destroy the answers we already had."""
    executable, _ = _counting_stub(tmp_path)
    cache = tmp_path / "llmfit-scan.json"
    await _advisor(executable, cache).scan(8192)
    before = cache.read_text()

    broken = tmp_path / "broken"
    broken.write_text(
        "#!/usr/bin/env python3\n"
        'import sys\nprint("llmfit 1.1.11") if "--version" in sys.argv else sys.exit(2)\n'
    )
    broken.chmod(0o755)
    await _advisor(broken, cache).scan(8192, refresh=True)

    assert cache.read_text() == before


async def test_no_cache_path_still_scans(tmp_path: Path) -> None:
    """Caching is an optimisation; the advisor works without one."""
    executable, _ = _counting_stub(tmp_path)

    result = await LlmfitAdvisor(executable, "1.1.11", 5).scan(8192)

    assert len(result.models) == 2
    assert result.models[0].fit is FitLevel.GOOD
