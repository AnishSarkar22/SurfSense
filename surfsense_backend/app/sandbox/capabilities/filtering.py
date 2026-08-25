"""Deterministic facet and policy filtering for capability retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from .schema import CapabilityEnvelope, CapabilityKind, CapabilityTier


@dataclass(frozen=True, slots=True)
class CapabilityFilter:
    domains: frozenset[str] = frozenset()
    kinds: frozenset[CapabilityKind] = frozenset()
    categories: frozenset[str] = frozenset()
    allowed_tiers: frozenset[CapabilityTier] = frozenset(CapabilityTier)
    excluded_ids: frozenset[str] = frozenset()
    maximum_natural_frames: int | None = None

    def __post_init__(self) -> None:
        if self.maximum_natural_frames is not None and self.maximum_natural_frames <= 0:
            raise ValueError("maximum_natural_frames must be positive")


def capability_matches(
    capability: CapabilityEnvelope[object],
    facets: CapabilityFilter,
) -> bool:
    """Return whether all requested facets and hard policy constraints match."""

    return not (
        (facets.domains and capability.domain not in facets.domains)
        or (facets.kinds and capability.kind not in facets.kinds)
        or (facets.categories and capability.category not in facets.categories)
        or capability.tier not in facets.allowed_tiers
        or capability.id in facets.excluded_ids
        or (
            facets.maximum_natural_frames is not None
            and capability.natural_frame_length is not None
            and capability.natural_frame_length > facets.maximum_natural_frames
        )
    )


def filter_capabilities(
    capabilities: tuple[CapabilityEnvelope[object], ...],
    facets: CapabilityFilter,
) -> tuple[CapabilityEnvelope[object], ...]:
    return tuple(
        capability
        for capability in capabilities
        if capability_matches(capability, facets)
    )
