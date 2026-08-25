"""Bounded loader for the authoritative sandbox-baked video skill."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath

import yaml

from app.sandbox import SandboxSession

_SKILL_ROOT = PurePosixPath("/opt/skills/video")
_SKILL_PATH = _SKILL_ROOT / "SKILL.md"
_MAX_SUPPLEMENTS = 8
_MAX_SKILL_BYTES = 96 * 1024


@dataclass(frozen=True, slots=True)
class LoadedVideoSkill:
    content: str
    sha256: str
    files: tuple[str, ...]


def _frontmatter(source: str) -> dict:
    if not source.startswith("---\n"):
        raise ValueError("video skill must start with YAML frontmatter")
    end = source.find("\n---\n", 4)
    if end == -1:
        raise ValueError("video skill frontmatter is not terminated")
    metadata = yaml.safe_load(source[4:end])
    if not isinstance(metadata, dict):
        raise ValueError("video skill frontmatter must be a mapping")
    return metadata


def _supplement_paths(metadata: dict) -> tuple[PurePosixPath, ...]:
    raw = metadata.get("supplement_allowlist")
    if not isinstance(raw, list) or not 1 <= len(raw) <= _MAX_SUPPLEMENTS:
        raise ValueError("video skill must declare a bounded supplement_allowlist")

    paths: list[PurePosixPath] = []
    for value in raw:
        if not isinstance(value, str):
            raise ValueError("video skill supplement paths must be strings")
        relative = PurePosixPath(value)
        resolved = _SKILL_ROOT / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.suffix.lower() != ".md"
            or not resolved.is_relative_to(_SKILL_ROOT)
        ):
            raise ValueError("video skill supplement path is unsafe")
        paths.append(resolved)
    if len(paths) != len(set(paths)):
        raise ValueError("video skill supplement paths must be unique")
    return tuple(paths)


async def load_video_skill(session: SandboxSession) -> LoadedVideoSkill:
    """Load the root and its closed supplement set from the live sandbox image."""
    root_bytes = await session.read_file(str(_SKILL_PATH))
    try:
        root = root_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("video skill must be UTF-8") from exc

    supplement_paths = _supplement_paths(_frontmatter(root))
    parts = [root]
    files = [str(_SKILL_PATH.relative_to(_SKILL_ROOT))]
    total_bytes = len(root_bytes)
    for path in supplement_paths:
        data = await session.read_file(str(path))
        total_bytes += len(data)
        if total_bytes > _MAX_SKILL_BYTES:
            raise ValueError("video skill exceeds its context budget")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"video skill supplement must be UTF-8: {path.name}") from exc
        relative = str(path.relative_to(_SKILL_ROOT))
        files.append(relative)
        parts.append(f"\n\n<!-- {relative} -->\n\n{text}")

    content = "".join(parts)
    return LoadedVideoSkill(
        content=content,
        sha256=hashlib.sha256(content.encode()).hexdigest(),
        files=tuple(files),
    )
