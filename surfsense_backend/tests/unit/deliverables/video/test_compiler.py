from __future__ import annotations

from collections.abc import Mapping

import pytest

from app.deliverables.video.compiler import (
    VideoCompilerError,
    compile_video_plan,
)
from app.deliverables.video.contracts import (
    AuthoredCapabilityLayer,
    AuthoredCapabilityProp,
    AuthoredTextLayer,
    AuthoredTransitionSelection,
    AuthoredVideoBeat,
    AuthoredVideoPlan,
    AuthoredVideoStyle,
    Bounds,
    Pacing,
    VideoPlan,
)
from app.sandbox.capabilities.disclosure import build_capability_disclosure
from app.sandbox.capabilities.retrieval import RetrievedCapability
from app.sandbox.capabilities.schema import (
    CapabilityEnvelope,
    CapabilityIndex,
    CapabilityKind,
    CapabilityTier,
)

pytestmark = pytest.mark.unit


def _capability(
    capability_id: str,
    kind: CapabilityKind,
    *,
    natural_frames: int | None = None,
    dependencies: tuple[str, ...] = (),
    props_schema: dict[str, object] | None = None,
) -> CapabilityEnvelope[dict[str, object]]:
    return CapabilityEnvelope[dict[str, object]](
        id=capability_id,
        kind=kind,
        domain="video",
        category=kind.value,
        summary=capability_id,
        tags=(kind.value,),
        natural_frame_length=natural_frames,
        tier=CapabilityTier.VETTED,
        dependencies=dependencies,
        props_schema=(
            props_schema or {"type": "object", "additionalProperties": False}
            if kind in {CapabilityKind.COMPONENT, CapabilityKind.TRANSITION}
            else None
        ),
        declaration={},
        search_text=f"{capability_id} {kind.value}",
    )


def _catalog() -> tuple[CapabilityIndex, object]:
    renderer = _capability("video.renderer.master", CapabilityKind.RENDERER)
    core = _capability(
        "video.component.core.primitives",
        CapabilityKind.COMPONENT,
    )
    font = _capability("font.inter", CapabilityKind.FONT)
    transition = _capability(
        "video.transition.whip-pan",
        CapabilityKind.TRANSITION,
        natural_frames=20,
    )
    shared = _capability("video.component.shared-base", CapabilityKind.COMPONENT)
    chart = _capability(
        "video.component.animated-chart",
        CapabilityKind.COMPONENT,
        natural_frames=120,
        dependencies=(shared.id,),
        props_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "data": {"type": "array", "items": {"type": "number"}},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
        },
    )
    index = CapabilityIndex(
        schema_version=1,
        build_id="build-compiler-1",
        capabilities=(renderer, core, font, transition, shared, chart),
    )
    disclosure = build_capability_disclosure(
        index.build_id,
        tuple(
            RetrievedCapability(
                capability=capability,
                score=10 - position,
                matched_terms=(),
            )
            for position, capability in enumerate((font, transition, chart))
        ),
    )
    return index, disclosure


def _authored(*, component_slot: str = "capability-03") -> AuthoredVideoPlan:
    return AuthoredVideoPlan(
        title="Quarterly update",
        language="en",
        style=AuthoredVideoStyle(
            primary_font_id="font.inter",
            palette=("#0B1020", "#FFFFFF"),
        ),
        beats=(
            AuthoredVideoBeat(
                beat_id="opening",
                utterance_id="opening-narration",
                narration="Revenue grew in every region.",
                pacing=Pacing.QUICK,
                layers=(
                    AuthoredCapabilityLayer(
                        type="capability",
                        id="chart",
                        bounds=Bounds(x=100, y=100, width=1200, height=700),
                        capability_slot=component_slot,
                    ),
                ),
                transition_to_next=AuthoredTransitionSelection(
                    capability_slot="capability-02"
                ),
            ),
            AuthoredVideoBeat(
                beat_id="close",
                utterance_id="close-narration",
                narration="The team is positioned for durable growth.",
                layers=(
                    AuthoredTextLayer(
                        type="text",
                        id="headline",
                        bounds=Bounds(x=100, y=100, width=1200, height=300),
                        text="Durable growth",
                        font_id="font.inter",
                        font_size=72,
                        color="#FFFFFF",
                    ),
                ),
            ),
        ),
    )


def _property_names(value: object) -> set[str]:
    if isinstance(value, Mapping):
        names = set(value.get("properties", {}))
        return names | {
            name for child in value.values() for name in _property_names(child)
        }
    if isinstance(value, list):
        return {name for child in value for name in _property_names(child)}
    return set()


def test_authored_schema_omits_compiler_owned_fields() -> None:
    names = _property_names(AuthoredVideoPlan.model_json_schema())

    assert {
        "min_duration_frames",
        "duration_frames",
        "selected_capability_ids",
        "build_id",
        "schema_version",
        "seed",
    }.isdisjoint(names)


def test_authored_capability_props_are_compiled_to_a_runtime_mapping() -> None:
    index, disclosure = _catalog()
    authored = _authored()
    chart = authored.beats[0].layers[0].model_copy(
        update={
            "props": (
                AuthoredCapabilityProp(key="data", value=(12.0, 18.0)),
                AuthoredCapabilityProp(key="labels", value=("Q1", "Q2")),
            )
        }
    )
    first_beat = authored.beats[0].model_copy(
        update={"layers": (chart,)},
    )
    authored = authored.model_copy(
        update={"beats": (first_beat, *authored.beats[1:])},
    )
    compiled = compile_video_plan(authored, index=index, disclosure=disclosure)

    assert compiled.beats[0].layers[0].props == {
        "data": [12.0, 18.0],
        "labels": ["Q1", "Q2"],
    }


def test_compiler_rejects_slot_used_as_the_wrong_kind() -> None:
    index, disclosure = _catalog()

    with pytest.raises(VideoCompilerError) as raised:
        compile_video_plan(
            _authored(component_slot="capability-02"),
            index=index,
            disclosure=disclosure,
        )

    diagnostic = raised.value.diagnostics[0]
    assert diagnostic.code == "wrong_capability_kind"
    assert diagnostic.capability_slot == "capability-02"
    assert diagnostic.path == ("beats", 0, "layers", 0, "capability_slot")


def test_compiler_is_deterministic_and_injects_capability_owned_values() -> None:
    index, disclosure = _catalog()

    first = compile_video_plan(_authored(), index=index, disclosure=disclosure)
    second = compile_video_plan(_authored(), index=index, disclosure=disclosure)

    assert first == second
    assert first.build_id == index.build_id
    assert first.selected_capability_ids == (
        "font.inter",
        "video.component.animated-chart",
        "video.component.core.primitives",
        "video.component.shared-base",
        "video.renderer.master",
        "video.transition.whip-pan",
    )
    assert first.beats[0].layers[0].capability_id == ("video.component.animated-chart")
    assert first.beats[0].min_duration_frames == 120
    assert first.beats[0].transition_to_next is not None
    assert first.beats[0].transition_to_next.duration_frames == 20
    assert first.beats[1].min_duration_frames == 90
    assert VideoPlan.model_validate(first.model_dump()) == first


def test_compiler_rejects_obvious_duration_overflow_before_tts() -> None:
    index, disclosure = _catalog()
    authored = _authored().model_copy(
        update={
            "beats": (
                _authored()
                .beats[0]
                .model_copy(update={"narration": ("word " * 999) + "end."}),
                _authored().beats[1],
            )
        }
    )

    with pytest.raises(VideoCompilerError) as raised:
        compile_video_plan(authored, index=index, disclosure=disclosure)

    diagnostic = raised.value.diagnostics[0]
    assert diagnostic.code == "estimated_duration_budget_exceeded"
    assert diagnostic.path == ("beats",)
    assert diagnostic.details["estimated_frames"] > diagnostic.details["budget_frames"]
    assert len(diagnostic.details["suggested_max_words"]) == 2
