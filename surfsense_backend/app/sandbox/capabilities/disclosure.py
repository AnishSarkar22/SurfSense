"""Bounded model-facing disclosure of retrieved capability metadata."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Final

from .retrieval import RetrievedCapability
from .schema import (
    CapabilityCandidate,
    CapabilityDisclosure,
    CapabilityIndex,
    materialize_json,
)

MAX_DISCLOSED_CAPABILITIES: Final = 48
MAX_DISCLOSURE_BYTES: Final = 128 * 1024


def _candidate(item: RetrievedCapability) -> CapabilityCandidate:
    capability = item.capability
    return CapabilityCandidate(
        id=capability.id,
        kind=capability.kind,
        category=capability.category,
        summary=capability.summary,
        tags=capability.tags,
        vibe=capability.vibe,
        use_for=capability.use_for,
        avoid_for=capability.avoid_for,
        natural_frame_length=capability.natural_frame_length,
        score=item.score,
        matched_terms=item.matched_terms,
        props_schema=materialize_json(capability.props_schema),
    )


def validate_disclosable_capabilities(index: CapabilityIndex) -> None:
    """Fail before billable planning if any indexed capability cannot be disclosed."""

    for capability in index.capabilities:
        candidate = _candidate(
            RetrievedCapability(
                capability=capability,
                score=0,
                matched_terms=(),
            )
        )
        candidate.model_dump_json()


def build_capability_disclosure(
    build_id: str,
    retrieved: Iterable[RetrievedCapability],
    *,
    max_candidates: int = MAX_DISCLOSED_CAPABILITIES,
    max_bytes: int = MAX_DISCLOSURE_BYTES,
) -> CapabilityDisclosure:
    """Deduplicate candidates and include exact schemas within fixed bounds."""

    if not 1 <= max_candidates <= MAX_DISCLOSED_CAPABILITIES:
        raise ValueError(
            f"max_candidates must be between 1 and {MAX_DISCLOSED_CAPABILITIES}"
        )
    if not 256 <= max_bytes <= MAX_DISCLOSURE_BYTES:
        raise ValueError(f"max_bytes must be between 256 and {MAX_DISCLOSURE_BYTES}")

    candidates: list[CapabilityCandidate] = []
    seen: set[str] = set()
    used_bytes = 0
    for item in retrieved:
        capability = item.capability
        if capability.id in seen:
            continue
        candidate = _candidate(item)
        candidate_bytes = len(
            json.dumps(
                candidate.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        )
        if used_bytes + candidate_bytes > max_bytes:
            if not candidates:
                raise ValueError("first capability exceeds the disclosure byte limit")
            continue
        candidates.append(candidate)
        seen.add(capability.id)
        used_bytes += candidate_bytes
        if len(candidates) == max_candidates:
            break

    if not candidates:
        raise ValueError("capability disclosure must contain at least one candidate")
    disclosed_ids = tuple(candidate.id for candidate in candidates)
    return CapabilityDisclosure(
        build_id=build_id,
        candidates=tuple(candidates),
        disclosed_ids=disclosed_ids,
    )
