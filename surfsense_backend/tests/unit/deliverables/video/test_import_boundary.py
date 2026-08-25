from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).parents[4]


def _imports_below(path: Path) -> set[str]:
    imports: set[str] = set()
    for source in path.rglob("*.py"):
        tree = ast.parse(source.read_text(), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module)
    return imports


def test_queued_and_legacy_video_paths_do_not_import_each_other() -> None:
    queued_imports = _imports_below(_ROOT / "app/deliverables/video")
    legacy_imports = _imports_below(_ROOT / "app/agents/video_presentation")

    assert not any(
        name == "app.agents.video_presentation"
        or name.startswith("app.agents.video_presentation.")
        for name in queued_imports
    )
    assert not any(
        name == "app.deliverables.video" or name.startswith("app.deliverables.video.")
        for name in legacy_imports
    )
