"""Deterministic lexical retrieval over the sandbox-generated capability index."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from .schema import (
    CapabilityId,
    CapabilityIndex,
    CapabilityKind,
    CapabilityTier,
)

_TERM = re.compile(r"[^\W_]+", re.UNICODE)
_WEIGHTS = {
    "use_for": 8,
    "tags": 5,
    "category": 4,
    "vibe": 4,
    "summary": 2,
    "all": 1,
    "avoid_for": -16,
}
_CREATIVE_KINDS = {CapabilityKind.COMPONENT, CapabilityKind.TRANSITION}


def _terms(query: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", query).casefold()
    return tuple(dict.fromkeys(_TERM.findall(normalized)))


def retrieve_capability_ids(
    index: CapabilityIndex,
    query: str,
    *,
    minimum: int = 8,
    maximum: int = 15,
    per_category: int = 3,
) -> tuple[CapabilityId, ...]:
    """Return a stable, diverse shortlist plus required core/font dependencies."""

    if not 1 <= minimum <= maximum <= 15:
        raise ValueError("capability retrieval requires 1 <= minimum <= maximum <= 15")
    if per_category < 1:
        raise ValueError("per_category must be positive")

    by_id = index.by_id()
    creative = {
        capability.id: capability
        for capability in index.capabilities
        if capability.kind in _CREATIVE_KINDS
        and capability.tier is not CapabilityTier.CORE
    }
    scores: Counter[str] = Counter()
    for term in _terms(query):
        for field_name, weight in _WEIGHTS.items():
            for capability_id in getattr(index.postings, field_name).get(term, ()):
                if capability_id in creative:
                    scores[capability_id] += weight

    selected: list[str] = []
    category_counts: Counter[str] = Counter()

    def dependency_closure(capability_id: str) -> list[str]:
        closure: list[str] = []
        visited = set(selected)

        def visit(current_id: str) -> None:
            for dependency_id in by_id[current_id].dependencies:
                if dependency_id in visited:
                    continue
                visited.add(dependency_id)
                if dependency_id in creative:
                    visit(dependency_id)
                    closure.append(dependency_id)

        visit(capability_id)
        return closure

    def add(capability_id: str) -> bool:
        if capability_id in selected:
            return False
        additions = [
            *dependency_closure(capability_id),
            capability_id,
        ]
        additions = list(dict.fromkeys(additions))
        added_categories = Counter(creative[item].category for item in additions)
        if len(selected) + len(additions) > maximum or any(
            category_counts[category] + count > per_category
            for category, count in added_categories.items()
        ):
            return False
        selected.extend(additions)
        category_counts.update(added_categories)
        return True

    ranked = sorted(creative, key=lambda capability_id: (-scores[capability_id], capability_id))
    for capability_id in ranked:
        if len(selected) >= maximum:
            break
        if scores[capability_id] > 0:
            add(capability_id)

    if len(selected) < minimum:
        fallback = sorted(
            creative,
            key=lambda capability_id: (
                creative[capability_id].tier is CapabilityTier.EXPERIMENTAL,
                -scores[capability_id],
                capability_id,
            ),
        )
        for capability_id in fallback:
            if len(selected) >= minimum:
                break
            if scores[capability_id] >= 0:
                add(capability_id)

    required = [
        capability.id
        for capability in index.capabilities
        if capability.kind is not CapabilityKind.RENDERER
        and (
            capability.kind is CapabilityKind.FONT
            or capability.tier is CapabilityTier.CORE
        )
    ]
    return tuple(dict.fromkeys((*required, *selected)))


__all__ = ["retrieve_capability_ids"]
