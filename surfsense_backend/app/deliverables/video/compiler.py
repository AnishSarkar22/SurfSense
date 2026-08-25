"""Deterministic compilation from the model-facing video contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from app.deliverables.jobs.policy import VIDEO_SPEC
from app.deliverables.video.contracts import (
    AuthoredCapabilityLayer,
    AuthoredMediaLayer,
    AuthoredShapeLayer,
    AuthoredTextLayer,
    AuthoredVideoPlan,
    CapabilityLayer,
    DeclarativeLayer,
    LayerTiming,
    MediaLayer,
    Pacing,
    ShapeLayer,
    TextLayer,
    TransitionSelection,
    VideoBeat,
    VideoPlan,
    VideoStyle,
)
from app.sandbox.capabilities.schema import (
    CapabilityCandidate,
    CapabilityDisclosure,
    CapabilityEnvelope,
    CapabilityIndex,
    CapabilityKind,
)
from app.sandbox.capabilities.validation import validate_capability_props

PACING_MIN_FRAMES: Final[Mapping[Pacing, int]] = {
    Pacing.QUICK: 45,
    Pacing.STANDARD: 90,
    Pacing.DELIBERATE: 150,
}
DEFAULT_TRANSITION_FRAMES: Final = 15
_FPS: Final = 30
_ESTIMATED_WORDS_PER_SECOND: Final = 2.5
_DURATION_SAFETY_FACTOR: Final = 0.95
_RENDERER_CAPABILITY_ID: Final = "video.renderer.master"
_CORE_PRIMITIVES_CAPABILITY_ID: Final = "video.component.core.primitives"


class VideoCompilerDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: Annotated[str, Field(min_length=1, max_length=64)]
    message: Annotated[str, Field(min_length=1, max_length=1000)]
    path: tuple[str | int, ...] = ()
    capability_slot: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class VideoCompilerError(ValueError):
    """Compilation failure carrying stable machine-readable diagnostics."""

    diagnostics: tuple[VideoCompilerDiagnostic, ...]

    def __init__(self, *diagnostics: VideoCompilerDiagnostic) -> None:
        if not diagnostics:
            raise ValueError("VideoCompilerError requires at least one diagnostic")
        self.diagnostics = tuple(diagnostics)
        super().__init__("; ".join(item.message for item in diagnostics))


def disclosed_capability_slots(
    disclosure: CapabilityDisclosure,
) -> tuple[tuple[str, CapabilityCandidate], ...]:
    """Assign stable attempt-local slots without exposing IDs in authored plans."""

    return tuple(
        (f"capability-{position:02d}", candidate)
        for position, candidate in enumerate(disclosure.candidates, start=1)
    )


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    capability_slot: str | None = None,
    details: dict[str, JsonValue] | None = None,
) -> VideoCompilerError:
    return VideoCompilerError(
        VideoCompilerDiagnostic(
            code=code,
            message=message,
            path=path,
            capability_slot=capability_slot,
            details=details or {},
        )
    )


class _Resolver:
    def __init__(
        self,
        index: CapabilityIndex,
        disclosure: CapabilityDisclosure,
    ) -> None:
        if index.build_id != disclosure.build_id:
            raise _error(
                "build_mismatch",
                f"capability index build {index.build_id!r} does not match "
                f"disclosure build {disclosure.build_id!r}",
            )
        self._by_id = index.by_id()
        self._slots = dict(disclosed_capability_slots(disclosure))

    def resolve_slot(
        self,
        slot: str,
        expected_kind: CapabilityKind,
        *,
        path: tuple[str | int, ...],
    ) -> CapabilityEnvelope[dict[str, object]]:
        candidate = self._slots.get(slot)
        if candidate is None:
            raise _error(
                "unknown_capability_slot",
                f"unknown disclosed capability slot: {slot!r}",
                path=path,
                capability_slot=slot,
            )
        if candidate.kind is not expected_kind:
            raise _error(
                "wrong_capability_kind",
                f"{slot!r} is a {candidate.kind.value} slot, not "
                f"a {expected_kind.value} slot",
                path=path,
                capability_slot=slot,
            )
        capability = self._by_id.get(candidate.id)
        if capability is None or capability.kind is not expected_kind:
            raise _error(
                "inconsistent_capability_disclosure",
                f"{slot!r} does not match the live capability index",
                path=path,
                capability_slot=slot,
            )
        return capability

    def resolve_font(
        self,
        capability_id: str,
        *,
        path: tuple[str | int, ...],
    ) -> CapabilityEnvelope[dict[str, object]]:
        candidate = next(
            (
                candidate
                for candidate in self._slots.values()
                if candidate.id == capability_id
            ),
            None,
        )
        if candidate is None:
            raise _error(
                "undisclosed_font",
                f"font capability was not disclosed: {capability_id!r}",
                path=path,
            )
        if candidate.kind is not CapabilityKind.FONT:
            raise _error(
                "wrong_capability_kind",
                f"{capability_id!r} is not a font capability",
                path=path,
            )
        capability = self._by_id.get(capability_id)
        if capability is None or capability.kind is not CapabilityKind.FONT:
            raise _error(
                "inconsistent_capability_disclosure",
                f"font {capability_id!r} does not match the live capability index",
                path=path,
            )
        return capability

    def resolve_required(
        self,
        capability_id: str,
        expected_kind: CapabilityKind,
    ) -> CapabilityEnvelope[dict[str, object]]:
        capability = self._by_id.get(capability_id)
        if capability is None or capability.kind is not expected_kind:
            raise _error(
                "missing_required_capability",
                f"live capability index lacks required {expected_kind.value} "
                f"{capability_id!r}",
            )
        return capability

    def selected_closure(self, roots: set[str]) -> tuple[str, ...]:
        selected = set(roots)
        pending = list(roots)
        while pending:
            capability_id = pending.pop()
            capability = self._by_id[capability_id]
            for dependency_id in capability.dependencies:
                if dependency_id not in selected:
                    selected.add(dependency_id)
                    pending.append(dependency_id)
        return tuple(sorted(selected))


def _validate_props(
    index: CapabilityIndex,
    capability_id: str,
    kind: CapabilityKind,
    props: Mapping[str, object],
    *,
    path: tuple[str | int, ...],
    slot: str,
) -> None:
    try:
        validate_capability_props(index, ((capability_id, kind, props),))
    except ValueError as exc:
        raise _error(
            "invalid_capability_props",
            str(exc),
            path=path,
            capability_slot=slot,
        ) from exc


def compile_video_plan(
    authored: AuthoredVideoPlan,
    *,
    index: CapabilityIndex,
    disclosure: CapabilityDisclosure,
) -> VideoPlan:
    """Compile an authored plan against one exact sandbox capability build."""

    resolver = _Resolver(index, disclosure)
    renderer = resolver.resolve_required(
        _RENDERER_CAPABILITY_ID, CapabilityKind.RENDERER
    )
    selected_roots: set[str] = {renderer.id}
    core_primitives: CapabilityEnvelope[dict[str, object]] | None = None

    primary_font = resolver.resolve_font(
        authored.style.primary_font_id,
        path=("style", "primary_font_id"),
    )
    selected_roots.add(primary_font.id)
    if authored.style.secondary_font_id is not None:
        secondary_font = resolver.resolve_font(
            authored.style.secondary_font_id,
            path=("style", "secondary_font_id"),
        )
        selected_roots.add(secondary_font.id)

    compiled_layers: list[tuple[DeclarativeLayer, ...]] = []
    beat_floors: list[int] = []
    transitions: list[TransitionSelection | None] = []
    for beat_index, beat in enumerate(authored.beats):
        floor = PACING_MIN_FRAMES[beat.pacing]
        layers: list[DeclarativeLayer] = []
        for layer_index, layer in enumerate(beat.layers):
            layer_path = ("beats", beat_index, "layers", layer_index)
            if isinstance(layer, AuthoredTextLayer):
                core_primitives = core_primitives or resolver.resolve_required(
                    _CORE_PRIMITIVES_CAPABILITY_ID, CapabilityKind.COMPONENT
                )
                selected_roots.add(core_primitives.id)
                font = resolver.resolve_font(
                    layer.font_id,
                    path=(*layer_path, "font_id"),
                )
                selected_roots.add(font.id)
                layers.append(
                    TextLayer(
                        **layer.model_dump(),
                        timing=LayerTiming(),
                    )
                )
            elif isinstance(layer, AuthoredShapeLayer):
                core_primitives = core_primitives or resolver.resolve_required(
                    _CORE_PRIMITIVES_CAPABILITY_ID, CapabilityKind.COMPONENT
                )
                selected_roots.add(core_primitives.id)
                layers.append(ShapeLayer(**layer.model_dump(), timing=LayerTiming()))
            elif isinstance(layer, AuthoredMediaLayer):
                core_primitives = core_primitives or resolver.resolve_required(
                    _CORE_PRIMITIVES_CAPABILITY_ID, CapabilityKind.COMPONENT
                )
                selected_roots.add(core_primitives.id)
                layers.append(MediaLayer(**layer.model_dump(), timing=LayerTiming()))
            elif isinstance(layer, AuthoredCapabilityLayer):
                capability = resolver.resolve_slot(
                    layer.capability_slot,
                    CapabilityKind.COMPONENT,
                    path=(*layer_path, "capability_slot"),
                )
                _validate_props(
                    index,
                    capability.id,
                    CapabilityKind.COMPONENT,
                    layer.props,
                    path=(*layer_path, "props"),
                    slot=layer.capability_slot,
                )
                selected_roots.add(capability.id)
                if capability.natural_frame_length is not None:
                    floor = max(floor, capability.natural_frame_length)
                layer_values = layer.model_dump(exclude={"capability_slot"})
                layers.append(
                    CapabilityLayer(
                        **layer_values,
                        timing=LayerTiming(),
                        capability_id=capability.id,
                    )
                )
        compiled_layers.append(tuple(layers))
        beat_floors.append(floor)

        if beat.transition_to_next is None:
            transitions.append(None)
            continue
        transition = resolver.resolve_slot(
            beat.transition_to_next.capability_slot,
            CapabilityKind.TRANSITION,
            path=("beats", beat_index, "transition_to_next", "capability_slot"),
        )
        _validate_props(
            index,
            transition.id,
            CapabilityKind.TRANSITION,
            beat.transition_to_next.props,
            path=("beats", beat_index, "transition_to_next", "props"),
            slot=beat.transition_to_next.capability_slot,
        )
        duration = transition.natural_frame_length or DEFAULT_TRANSITION_FRAMES
        if duration > 120:
            raise _error(
                "transition_duration_out_of_range",
                f"transition {transition.id!r} requires {duration} frames; "
                "the current VideoPlan limit is 120",
                path=("beats", beat_index, "transition_to_next"),
                capability_slot=beat.transition_to_next.capability_slot,
            )
        selected_roots.add(transition.id)
        transitions.append(
            TransitionSelection(
                capability_id=transition.id,
                duration_frames=duration,
                props=beat.transition_to_next.props,
            )
        )

    for beat_index, transition in enumerate(transitions[:-1]):
        if transition is not None:
            transition_floor = transition.duration_frames * 2
            beat_floors[beat_index] = max(beat_floors[beat_index], transition_floor)
            beat_floors[beat_index + 1] = max(
                beat_floors[beat_index + 1], transition_floor
            )

    overlap_frames = sum(
        transition.duration_frames
        for transition in transitions
        if transition is not None
    )
    estimated_audio_frames = [
        round(len(beat.narration.split()) / _ESTIMATED_WORDS_PER_SECOND * _FPS)
        for beat in authored.beats
    ]
    estimated_duration_frames = (
        sum(
            max(floor, audio_frames)
            for floor, audio_frames in zip(
                beat_floors, estimated_audio_frames, strict=True
            )
        )
        - overlap_frames
    )
    narration_budget_frames = int(
        VIDEO_SPEC.max_duration_seconds * _FPS * _DURATION_SAFETY_FACTOR
    )
    if estimated_duration_frames > narration_budget_frames:
        gross_budget = narration_budget_frames + overlap_frames
        floor_total = sum(beat_floors)
        available_excess = max(0, gross_budget - floor_total)
        current_excess = [
            max(0, audio_frames - floor)
            for floor, audio_frames in zip(
                beat_floors, estimated_audio_frames, strict=True
            )
        ]
        excess_total = sum(current_excess)
        target_frames = [
            floor + (available_excess * excess // excess_total if excess_total else 0)
            for floor, excess in zip(beat_floors, current_excess, strict=True)
        ]
        raise _error(
            "estimated_duration_budget_exceeded",
            "authored narration and visual floors exceed the pre-TTS duration budget",
            path=("beats",),
            details={
                "estimated_frames": estimated_duration_frames,
                "budget_frames": narration_budget_frames,
                "suggested_max_words": [
                    max(
                        1,
                        int(frames / _FPS * _ESTIMATED_WORDS_PER_SECOND),
                    )
                    for frames in target_frames
                ],
            },
        )

    selected_capability_ids = resolver.selected_closure(selected_roots)
    if len(selected_capability_ids) > 64:
        raise _error(
            "capability_closure_too_large",
            "selected capability dependency closure exceeds 64 entries",
        )

    beats = tuple(
        VideoBeat(
            beat_id=beat.beat_id,
            utterance_id=beat.utterance_id,
            narration=beat.narration,
            layers=compiled_layers[position],
            min_duration_frames=beat_floors[position],
            transition_to_next=transitions[position],
        )
        for position, beat in enumerate(authored.beats)
    )
    try:
        return VideoPlan(
            build_id=index.build_id,
            title=authored.title,
            language=authored.language,
            selected_capability_ids=selected_capability_ids,
            style=VideoStyle(**authored.style.model_dump()),
            assets=authored.assets,
            beats=beats,
        )
    except ValidationError as exc:
        raise _error(
            "invalid_compiled_plan",
            f"compiled VideoPlan is invalid: {exc}",
        ) from exc


__all__ = [
    "PACING_MIN_FRAMES",
    "VideoCompilerDiagnostic",
    "VideoCompilerError",
    "compile_video_plan",
    "disclosed_capability_slots",
]
