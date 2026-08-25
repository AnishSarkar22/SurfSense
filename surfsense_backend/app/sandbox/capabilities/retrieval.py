"""Small deterministic lexical retrieval over the validated in-memory index."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Final

from .filtering import CapabilityFilter, capability_matches
from .schema import CapabilityEnvelope, CapabilityIndex, CapabilityTier

DEFAULT_TOP_K: Final = 6
MAX_TOP_K: Final = 8


def _tokens(value: str) -> frozenset[str]:
    normalized = unicodedata.normalize("NFKD", value).lower()
    tokens: list[str] = []
    current: list[str] = []
    for character in normalized:
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return frozenset(tokens)


def _field_tokens(values: tuple[str, ...]) -> frozenset[str]:
    return _tokens(" ".join(values))


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    text: str
    facets: CapabilityFilter = field(default_factory=CapabilityFilter)
    desired_vibe: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    top_k: int = DEFAULT_TOP_K

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("retrieval text must not be empty")
        if not 1 <= self.top_k <= MAX_TOP_K:
            raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")


@dataclass(frozen=True, slots=True)
class RetrievedCapability:
    capability: CapabilityEnvelope[dict[str, object]]
    score: int
    matched_terms: tuple[str, ...]


def _score(
    index: CapabilityIndex,
    query_terms: frozenset[str],
    vibe_terms: frozenset[str],
    avoid_terms: frozenset[str],
) -> tuple[dict[str, int], dict[str, set[str]]]:
    scores: defaultdict[str, int] = defaultdict(int)
    matched: defaultdict[str, set[str]] = defaultdict(set)

    def apply(
        field_name: str,
        terms: frozenset[str],
        weight: int,
        *,
        record_matches: bool = False,
    ) -> None:
        postings = getattr(index.postings, field_name)
        for term in terms:
            for capability_id in postings.get(term, ()):
                scores[capability_id] += weight
                if record_matches:
                    matched[capability_id].add(term)

    apply("all", query_terms, 1, record_matches=True)
    apply("tags", query_terms, 9)
    apply("use_for", query_terms, 7)
    apply("summary", query_terms, 4)
    apply("vibe", query_terms, 3)
    apply("category", query_terms, 2)
    apply("avoid_for", query_terms, -11)
    apply("vibe", vibe_terms, 5)
    apply("all", avoid_terms, -8)
    return dict(scores), dict(matched)


def retrieve_capabilities(
    index: CapabilityIndex,
    query: RetrievalQuery,
) -> tuple[RetrievedCapability, ...]:
    """Rank one visual intent and greedily retain category/tag diversity."""

    query_terms = _tokens(query.text)
    vibe_terms = _field_tokens(query.desired_vibe)
    avoid_terms = _field_tokens(query.avoid)
    scores, matched_terms = _score(index, query_terms, vibe_terms, avoid_terms)
    by_id = index.by_id()
    candidate_ids = set(scores)
    candidate_ids.update(
        capability.id
        for capability in index.capabilities
        if capability.tier is CapabilityTier.CORE
    )

    ranked: list[RetrievedCapability] = []
    for capability_id in sorted(candidate_ids):
        capability = by_id[capability_id]
        if not capability_matches(capability, query.facets):
            continue
        ranked.append(
            RetrievedCapability(
                capability=capability,
                score=scores.get(capability_id, 0)
                + (1 if capability.tier is CapabilityTier.CORE else 0),
                matched_terms=tuple(sorted(matched_terms.get(capability_id, ()))),
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.capability.id))

    selected: list[RetrievedCapability] = []
    selected_categories: set[str] = set()
    selected_tag_sets: list[frozenset[str]] = []
    remaining = ranked.copy()
    while remaining and len(selected) < query.top_k:
        reranked: list[tuple[int, str, RetrievedCapability]] = []
        for item in remaining:
            tags = frozenset(item.capability.tags)
            duplicate_penalty = (
                3 if item.capability.category in selected_categories else 0
            )
            duplicate_penalty += max(
                (len(tags & selected_tags) * 2 for selected_tags in selected_tag_sets),
                default=0,
            )
            reranked.append((item.score - duplicate_penalty, item.capability.id, item))
        _, _, chosen = min(reranked, key=lambda item: (-item[0], item[1]))
        selected.append(chosen)
        selected_categories.add(chosen.capability.category)
        selected_tag_sets.append(frozenset(chosen.capability.tags))
        remaining.remove(chosen)

    # Core primitives are authoring fallbacks, even when specialized lexical
    # matches are weak. Replace the lowest-ranked result if the bound is full.
    if selected and not any(
        item.capability.tier is CapabilityTier.CORE for item in selected
    ):
        fallback = next(
            (item for item in ranked if item.capability.tier is CapabilityTier.CORE),
            None,
        )
        if fallback is not None:
            if len(selected) == query.top_k:
                selected[-1] = fallback
            else:
                selected.append(fallback)

    return tuple(selected)
