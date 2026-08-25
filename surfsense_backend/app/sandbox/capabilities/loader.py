"""Load capability metadata from the exact live sandbox used by an attempt."""

from __future__ import annotations

import json
import re
from typing import Final

from app.sandbox import SandboxSession

from .schema import CAPABILITY_SCHEMA_VERSION, CapabilityIndex

CAPABILITY_INDEX_PATH: Final = "/opt/surfsense/capabilities/index.json"
MAX_CAPABILITY_INDEX_BYTES: Final = 8 * 1024 * 1024
_IMMUTABLE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_index_cache: dict[tuple[str, str], CapabilityIndex] = {}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _parse_index(data: bytes) -> CapabilityIndex:
    if not data:
        raise ValueError("capability index is empty")
    if len(data) > MAX_CAPABILITY_INDEX_BYTES:
        raise ValueError("capability index exceeds the trusted size limit")
    try:
        document = json.loads(
            data,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("capability index is not valid UTF-8 JSON") from exc
    return CapabilityIndex.model_validate_json(
        json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    )


async def load_capability_index(
    sandbox: SandboxSession,
    *,
    image_digest: str | None,
    expected_build_id: str | None = None,
) -> CapabilityIndex:
    """Read and validate the live index, caching only immutable image content.

    The file is always read from the newly acquired sandbox. Mutable tags never
    reuse parsed state. Immutable digests may reuse a parsed object only when
    both the digest and the live file's build ID agree.
    """

    data = await sandbox.read_file(CAPABILITY_INDEX_PATH)
    parsed = _parse_index(data)
    if parsed.schema_version != CAPABILITY_SCHEMA_VERSION:
        # Kept explicit at the loader boundary even though the model is strict.
        raise ValueError(
            f"expected capability schema {CAPABILITY_SCHEMA_VERSION!r}, "
            f"got {parsed.schema_version!r}"
        )
    if expected_build_id is not None and parsed.build_id != expected_build_id:
        raise ValueError(
            f"capability build mismatch: expected {expected_build_id!r}, "
            f"got {parsed.build_id!r}"
        )
    if image_digest is None or _IMMUTABLE_DIGEST.fullmatch(image_digest) is None:
        return parsed

    key = (image_digest, parsed.build_id)
    cached = _index_cache.get(key)
    if cached is not None:
        return cached
    _index_cache[key] = parsed
    return parsed


def clear_capability_index_cache() -> None:
    """Clear process state for tests and worker lifecycle hooks."""

    _index_cache.clear()
