"""Strict, generic contracts for a sandbox-provided capability index."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

CAPABILITY_SCHEMA_VERSION = 1
CapabilityId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=160,
        pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$",
    ),
]


class StrictCapabilityModel(BaseModel):
    """Shared trust-boundary behavior for index models."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _FrozenDict(dict[str, Any]):
    """JSON-serializable mapping that rejects mutation after construction."""

    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("capability index mappings are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze_json(child) for key, child in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_json(child) for child in value)
    return value


def materialize_json(value: Any) -> Any:
    """Return plain dict/list JSON from the immutable catalog representation."""

    if isinstance(value, dict):
        return {key: materialize_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [materialize_json(child) for child in value]
    return value


class CapabilityKind(StrEnum):
    FONT = "font"
    COMPONENT = "component"
    TRANSITION = "transition"
    RENDERER = "renderer"


class CapabilityTier(StrEnum):
    CORE = "core"
    VETTED = "vetted"
    EXPERIMENTAL = "experimental"


class NativeCanvas(StrictCapabilityModel):
    width: Annotated[int, Field(gt=0, le=7680)]
    height: Annotated[int, Field(gt=0, le=4320)]


class CapabilityPostings(StrictCapabilityModel):
    """Build-generated weighted inverted indexes keyed by normalized term."""

    all: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    tags: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    use_for: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    summary: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    vibe: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    category: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)
    avoid_for: dict[str, tuple[CapabilityId, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalized_unique_terms(self) -> CapabilityPostings:
        for field_name in type(self).model_fields:
            postings = getattr(self, field_name)
            for term, capability_ids in postings.items():
                if not term or term != term.strip().casefold():
                    raise ValueError("posting terms must be normalized")
                if len(capability_ids) != len(set(capability_ids)):
                    raise ValueError(
                        f"posting {field_name}.{term!r} contains duplicate IDs"
                    )
            object.__setattr__(self, field_name, _FrozenDict(postings))
        return self


class CapabilityEnvelope[PayloadT](StrictCapabilityModel):
    """Kind-neutral metadata surrounding a kind-specific declaration."""

    id: CapabilityId
    kind: CapabilityKind
    domain: Annotated[str, Field(min_length=1, max_length=64)]
    category: Annotated[str, Field(min_length=1, max_length=96)]
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    tags: Annotated[tuple[str, ...], Field(max_length=32)] = ()
    vibe: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    use_for: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    avoid_for: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    natural_frame_length: Annotated[int | None, Field(gt=0, le=5400)] = None
    tier: CapabilityTier
    dependencies: Annotated[tuple[CapabilityId, ...], Field(max_length=32)] = ()
    native_canvas: NativeCanvas | None = None
    props_schema: dict[str, JsonValue] | None = None
    deterministic_test_props: dict[str, JsonValue] | None = None
    upstream_docs_url: Annotated[str | None, Field(max_length=2048)] = None
    vendored_revision: Annotated[str | None, Field(max_length=160)] = None
    declaration: PayloadT
    search_text: Annotated[str, Field(min_length=1, max_length=8000)]

    @model_validator(mode="after")
    def unique_normalized_terms(self) -> CapabilityEnvelope[PayloadT]:
        for field_name in ("tags", "vibe", "use_for", "avoid_for", "dependencies"):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.id in self.dependencies:
            raise ValueError("a capability cannot depend on itself")
        for field_name in (
            "props_schema",
            "deterministic_test_props",
            "declaration",
        ):
            object.__setattr__(
                self,
                field_name,
                _freeze_json(getattr(self, field_name)),
            )
        return self


class CapabilityIndex(StrictCapabilityModel):
    """Validated index generated inside the exact sandbox image."""

    schema_version: Literal[1]
    build_id: Annotated[
        str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    ]
    runtime_build_id: Annotated[
        str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    ] | None = None
    capabilities: tuple[CapabilityEnvelope[dict[str, Any]], ...]
    postings: CapabilityPostings = Field(default_factory=CapabilityPostings)

    @model_validator(mode="after")
    def internally_consistent(self) -> CapabilityIndex:
        if self.schema_version != CAPABILITY_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported capability schema version: {self.schema_version!r}"
            )
        ids = [capability.id for capability in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("capability IDs must be unique")
        known_ids = set(ids)
        for capability in self.capabilities:
            missing = set(capability.dependencies) - known_ids
            if missing:
                raise ValueError(
                    f"{capability.id} has unresolved dependencies: {sorted(missing)}"
                )
        for field_name in type(self.postings).model_fields:
            for term, posting_ids in getattr(self.postings, field_name).items():
                unknown = set(posting_ids) - known_ids
                if unknown:
                    raise ValueError(
                        f"posting {field_name}.{term!r} refers to unknown IDs: "
                        f"{sorted(unknown)}"
                    )
        return self

    def by_id(self) -> dict[str, CapabilityEnvelope[dict[str, Any]]]:
        return {capability.id: capability for capability in self.capabilities}


class CapabilityCandidate(StrictCapabilityModel):
    id: CapabilityId
    kind: CapabilityKind
    category: Annotated[str, Field(min_length=1, max_length=96)]
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    tags: Annotated[tuple[str, ...], Field(max_length=32)] = ()
    vibe: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    use_for: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    avoid_for: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    natural_frame_length: Annotated[int | None, Field(gt=0, le=5400)] = None
    score: int
    matched_terms: tuple[str, ...] = ()
    props_schema: dict[str, JsonValue] | None = None


class CapabilityDisclosure(StrictCapabilityModel):
    build_id: Annotated[str, Field(min_length=1, max_length=128)]
    candidates: Annotated[tuple[CapabilityCandidate, ...], Field(max_length=48)]
    disclosed_ids: Annotated[tuple[CapabilityId, ...], Field(max_length=48)]

    @model_validator(mode="after")
    def ids_match_candidates(self) -> CapabilityDisclosure:
        candidate_ids = tuple(candidate.id for candidate in self.candidates)
        if candidate_ids != self.disclosed_ids:
            raise ValueError("disclosed_ids must match candidate order exactly")
        if len(self.disclosed_ids) != len(set(self.disclosed_ids)):
            raise ValueError("disclosed capability IDs must be unique")
        return self
