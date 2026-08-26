"""Deterministic 1920x1080@30 compilation from measured narration."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final, Protocol

from app.deliverables.jobs.policy import VIDEO_SPEC

from .contracts import (
    AssetKind,
    CapabilityLayer,
    MediaLayer,
    NarrationTrack,
    RenderAudioTrack,
    RenderBeat,
    RenderCapabilityLayer,
    RenderMediaLayer,
    RenderShapeLayer,
    RenderTextLayer,
    RenderTransition,
    ShapeLayer,
    TextLayer,
    TimelineBeat,
    TimelineLayer,
    TimelineTransition,
    VideoPlan,
    VideoRenderInput,
    VideoTimeline,
)

WIDTH: Final = 1920
HEIGHT: Final = 1080
FPS: Final = 30
SAFE_MARGIN: Final = 72
MAX_GENERATED_ELEMENTS: Final = 200
TARGET_MAX_FRAMES: Final = VIDEO_SPEC.max_duration_seconds * FPS
HARD_MAX_FRAMES: Final = VIDEO_SPEC.hard_max_duration_seconds * FPS
WORDS_PER_SECOND: Final = 2.5


@dataclass(frozen=True, slots=True)
class NarrationBudget:
    beat_id: str
    max_seconds: float
    max_words: int


class VideoTimelineDurationError(ValueError):
    """A compacted timeline still exceeds the trusted duration limit."""

    def __init__(
        self,
        *,
        compiled_frames: int,
        suggested_narration_budgets: tuple[NarrationBudget, ...],
    ) -> None:
        self.max_frames = HARD_MAX_FRAMES
        self.compiled_frames = compiled_frames
        self.overflow_frames = compiled_frames - self.max_frames
        self.suggested_narration_budgets = suggested_narration_budgets
        super().__init__(
            f"compiled video exceeds the {VIDEO_SPEC.hard_max_duration_seconds}-second "
            f"limit by {self.overflow_frames} frames"
        )


class MeasuredNarration(Protocol):
    beat_id: str
    utterance_id: str
    audio: str
    duration_seconds: float


def _stable_seed(plan: VideoPlan, beat_id: str) -> int:
    digest = hashlib.sha256(
        f"{plan.build_id}\0{plan.title}\0{beat_id}".encode()
    ).digest()
    return int.from_bytes(digest[:4])


def normalize_video_plan(plan: VideoPlan) -> VideoPlan:
    """Canonicalize unordered collections and fill deterministic beat seeds."""

    return plan.model_copy(
        update={
            "selected_capability_ids": tuple(sorted(plan.selected_capability_ids)),
            "assets": tuple(sorted(plan.assets, key=lambda asset: asset.id)),
            "beats": tuple(
                beat
                if beat.seed is not None
                else beat.model_copy(update={"seed": _stable_seed(plan, beat.beat_id)})
                for beat in plan.beats
            ),
        }
    )


def _narration_value(item: object, name: str) -> object:
    if isinstance(item, Mapping):
        try:
            return item[name]
        except KeyError:
            raise ValueError(f"measured narration is missing {name!r}") from None
    try:
        return getattr(item, name)
    except AttributeError:
        raise ValueError(f"measured narration is missing {name!r}") from None


def _validate_audio_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("measured narration audio must be a non-empty path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\x00" in value:
        raise ValueError("measured narration audio must be a confined public path")
    return value


def _measured_by_beat(
    narration: Sequence[object],
) -> dict[str, tuple[str, str, float]]:
    result: dict[str, tuple[str, str, float]] = {}
    utterance_ids: set[str] = set()
    for item in narration:
        beat_id = _narration_value(item, "beat_id")
        utterance_id = _narration_value(item, "utterance_id")
        duration = _narration_value(item, "duration_seconds")
        if not isinstance(beat_id, str) or not isinstance(utterance_id, str):
            raise ValueError("measured narration identities must be strings")
        if beat_id in result or utterance_id in utterance_ids:
            raise ValueError("measured narration identities must be unique")
        if isinstance(duration, bool) or not isinstance(duration, int | float):
            raise ValueError("measured narration duration must be numeric")
        duration_float = float(duration)
        if not math.isfinite(duration_float) or duration_float <= 0:
            raise ValueError("measured narration duration must be positive and finite")
        result[beat_id] = (
            utterance_id,
            _validate_audio_path(_narration_value(item, "audio")),
            duration_float,
        )
        utterance_ids.add(utterance_id)
    return result


def _validate_layer_bounds(plan: VideoPlan) -> int:
    generated_elements = 0
    for beat in plan.beats:
        for layer in beat.layers:
            bounds = layer.bounds
            if bounds.x + bounds.width > WIDTH or bounds.y + bounds.height > HEIGHT:
                raise ValueError(f"layer {layer.id!r} exceeds the 1920x1080 canvas")
            if layer.safe_margin and (
                bounds.x < SAFE_MARGIN
                or bounds.y < SAFE_MARGIN
                or bounds.x + bounds.width > WIDTH - SAFE_MARGIN
                or bounds.y + bounds.height > HEIGHT - SAFE_MARGIN
            ):
                raise ValueError(f"layer {layer.id!r} exceeds the title-safe margin")
            generated_elements += (
                layer.generated_elements if isinstance(layer, CapabilityLayer) else 1
            )
    if generated_elements > MAX_GENERATED_ELEMENTS:
        raise ValueError(
            f"video generates {generated_elements} elements; "
            f"the limit is {MAX_GENERATED_ELEMENTS}"
        )
    return generated_elements


@dataclass(frozen=True, slots=True)
class _CompiledTimeline:
    duration_frames: int
    beats: tuple[TimelineBeat, ...]
    layers: tuple[TimelineLayer, ...]
    transitions: tuple[TimelineTransition, ...]
    narration: tuple[NarrationTrack, ...]


def _compile_with_floors(
    plan: VideoPlan,
    measured: Mapping[str, tuple[str, str, float]],
    floors: Sequence[int],
    audio_frames: Sequence[int],
) -> _CompiledTimeline:
    for index, beat in enumerate(plan.beats[:-1]):
        transition = beat.transition_to_next
        if transition is not None and transition.duration_frames * 2 > min(
            max(floors[index], audio_frames[index]),
            max(floors[index + 1], audio_frames[index + 1]),
        ):
            raise ValueError(
                f"transition after {beat.beat_id!r} exceeds half an adjacent beat"
            )

    timeline_beats: list[TimelineBeat] = []
    timeline_layers: list[TimelineLayer] = []
    timeline_transitions: list[TimelineTransition] = []
    narration_tracks: list[NarrationTrack] = []
    previous_end = 0
    previous_narration_end = 0

    for index, beat in enumerate(plan.beats):
        overlap = (
            plan.beats[index - 1].transition_to_next.duration_frames
            if index > 0 and plan.beats[index - 1].transition_to_next is not None
            else 0
        )
        beat_start = previous_end - overlap
        narration_start = max(beat_start, previous_narration_end)
        narration_end = narration_start + audio_frames[index]
        beat_end = max(beat_start + floors[index], narration_end)
        utterance_id, audio, duration_seconds = measured[beat.beat_id]
        if utterance_id != beat.utterance_id:
            raise ValueError(f"utterance identity mismatch for beat {beat.beat_id!r}")

        timeline_beats.append(
            TimelineBeat(
                beat_id=beat.beat_id,
                utterance_id=beat.utterance_id,
                from_frame=beat_start,
                to_frame=beat_end,
                seed=beat.seed
                if beat.seed is not None
                else _stable_seed(plan, beat.beat_id),
            )
        )
        narration_tracks.append(
            NarrationTrack(
                beat_id=beat.beat_id,
                utterance_id=beat.utterance_id,
                audio=audio,
                from_frame=narration_start,
                to_frame=narration_end,
                duration_seconds=duration_seconds,
            )
        )
        for layer in beat.layers:
            layer_end = (
                layer.timing.end_frame
                if layer.timing.end_frame is not None
                else beat_end - beat_start
            )
            if layer_end > beat_end - beat_start:
                raise ValueError(
                    f"layer {layer.id!r} extends beyond beat {beat.beat_id!r}"
                )
            timeline_layers.append(
                TimelineLayer(
                    beat_id=beat.beat_id,
                    layer=layer,
                    from_frame=beat_start + layer.timing.start_frame,
                    to_frame=beat_start + layer_end,
                )
            )

        if index > 0:
            prior = plan.beats[index - 1]
            transition = prior.transition_to_next
            if transition is not None:
                timeline_transitions.append(
                    TimelineTransition(
                        capability_id=transition.capability_id,
                        from_beat_id=prior.beat_id,
                        to_beat_id=beat.beat_id,
                        from_frame=beat_start,
                        to_frame=beat_start + transition.duration_frames,
                        props=transition.props,
                    )
                )
        previous_end = beat_end
        previous_narration_end = narration_end

    return _CompiledTimeline(
        duration_frames=previous_end,
        beats=tuple(timeline_beats),
        layers=tuple(timeline_layers),
        transitions=tuple(timeline_transitions),
        narration=tuple(narration_tracks),
    )


def compile_video_timeline(
    plan: VideoPlan,
    narration: Sequence[object],
    *,
    capability_natural_frames: Mapping[str, int] | None = None,
) -> VideoTimeline:
    """Compile authoritative audio measurements into absolute frame intervals."""

    normalized = normalize_video_plan(plan)
    _validate_layer_bounds(normalized)
    measured = _measured_by_beat(narration)
    expected_beats = {beat.beat_id for beat in normalized.beats}
    if set(measured) != expected_beats:
        missing = expected_beats - set(measured)
        extra = set(measured) - expected_beats
        raise ValueError(
            f"narration coverage mismatch; missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )
    natural_frames = capability_natural_frames or {}
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in natural_frames.values()
    ):
        raise ValueError("capability natural frame lengths must be positive integers")

    capability_floors: list[int] = []
    floors: list[int] = []
    audio_frames: list[int] = []
    for beat in normalized.beats:
        capability_floor = max(
            (
                natural_frames.get(layer.capability_id, 1)
                for layer in beat.layers
                if isinstance(layer, CapabilityLayer)
            ),
            default=1,
        )
        capability_floors.append(capability_floor)
        floors.append(max(beat.min_duration_frames, capability_floor))
        audio_frames.append(math.ceil(measured[beat.beat_id][2] * FPS))

    compiled = _compile_with_floors(normalized, measured, floors, audio_frames)
    if compiled.duration_frames > TARGET_MAX_FRAMES:
        compiled = _compile_with_floors(
            normalized, measured, capability_floors, audio_frames
        )
    if compiled.duration_frames > HARD_MAX_FRAMES:
        overlap_frames = sum(
            transition.to_frame - transition.from_frame
            for transition in compiled.transitions
        )
        available_excess = max(
            0,
            TARGET_MAX_FRAMES + overlap_frames - sum(capability_floors),
        )
        current_excess = [
            max(0, frames - floor)
            for frames, floor in zip(audio_frames, capability_floors, strict=True)
        ]
        excess_total = sum(current_excess)
        target_audio_frames = [
            floor + (available_excess * excess // excess_total if excess_total else 0)
            for floor, excess in zip(capability_floors, current_excess, strict=True)
        ]
        raise VideoTimelineDurationError(
            compiled_frames=compiled.duration_frames,
            suggested_narration_budgets=tuple(
                NarrationBudget(
                    beat_id=beat.beat_id,
                    max_seconds=target_frames / FPS,
                    max_words=max(
                        1,
                        math.floor(target_frames / FPS * WORDS_PER_SECOND),
                    ),
                )
                for beat, target_frames in zip(
                    normalized.beats, target_audio_frames, strict=True
                )
            ),
        )
    return VideoTimeline(
        duration_frames=compiled.duration_frames,
        beats=compiled.beats,
        layers=compiled.layers,
        transitions=compiled.transitions,
        narration=compiled.narration,
    )


def build_video_render_input(
    plan: VideoPlan,
    narration: Sequence[object],
    *,
    skill_version: str,
    capability_natural_frames: Mapping[str, int] | None = None,
) -> VideoRenderInput:
    normalized = normalize_video_plan(plan)
    timeline = compile_video_timeline(
        normalized,
        narration,
        capability_natural_frames=capability_natural_frames,
    )
    timeline_beat_by_id = {beat.beat_id: beat for beat in timeline.beats}
    assets = {asset.id: asset for asset in normalized.assets}
    layers_by_beat: dict[str, list] = {beat.beat_id: [] for beat in normalized.beats}
    for item in timeline.layers:
        beat = timeline_beat_by_id[item.beat_id]
        layer = item.layer
        placement = {
            "id": layer.id,
            "from": item.from_frame - beat.from_frame,
            "duration_in_frames": item.to_frame - item.from_frame,
            "x": layer.bounds.x,
            "y": layer.bounds.y,
            "width": layer.bounds.width,
            "height": layer.bounds.height,
        }
        if isinstance(layer, TextLayer):
            rendered = RenderTextLayer(
                type="text",
                **placement,
                text=layer.text,
                color=layer.color,
                font_id=layer.font_id,
                font_size=layer.font_size,
            )
        elif isinstance(layer, ShapeLayer):
            rendered = RenderShapeLayer(
                type="shape",
                **placement,
                shape=layer.shape,
                fill=layer.fill,
            )
        elif isinstance(layer, MediaLayer):
            asset = assets[layer.asset_id]
            if asset.kind is AssetKind.AUDIO:
                raise ValueError("audio assets cannot be used as visual layers")
            rendered = RenderMediaLayer(
                type="video" if asset.kind is AssetKind.VIDEO else "image",
                **placement,
                src=asset.path,
                fit=layer.fit,
            )
        elif isinstance(layer, CapabilityLayer):
            rendered = RenderCapabilityLayer(
                type="component",
                **placement,
                capability_id=layer.capability_id,
                props=layer.props,
            )
        else:
            raise TypeError(f"unsupported declarative layer: {type(layer).__name__}")
        layers_by_beat[item.beat_id].append(rendered)

    return VideoRenderInput(
        build_id=normalized.build_id,
        skill_version=skill_version,
        max_duration_seconds=VIDEO_SPEC.hard_max_duration_seconds,
        duration_in_frames=timeline.duration_frames,
        selected_capability_ids=normalized.selected_capability_ids,
        beats=tuple(
            RenderBeat(
                id=beat.beat_id,
                utterance_id=beat.utterance_id,
                start_frame=beat.from_frame,
                duration_in_frames=beat.to_frame - beat.from_frame,
                background=normalized.style.background,
                layers=tuple(layers_by_beat[beat.beat_id]),
            )
            for beat in timeline.beats
        ),
        transitions=tuple(
            RenderTransition(
                capability_id=transition.capability_id,
                from_beat_id=transition.from_beat_id,
                to_beat_id=transition.to_beat_id,
                start_frame=transition.from_frame,
                duration_in_frames=transition.to_frame - transition.from_frame,
                props=transition.props,
            )
            for transition in timeline.transitions
        ),
        audio_tracks=tuple(
            RenderAudioTrack(
                utterance_id=track.utterance_id,
                src=track.audio,
                start_frame=track.from_frame,
                duration_in_frames=track.to_frame - track.from_frame,
            )
            for track in timeline.narration
        ),
        seed=hashlib.sha256(
            f"{normalized.build_id}\0{normalized.title}".encode()
        ).hexdigest(),
    )
