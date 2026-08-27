"""Deterministic 1920x1080@30 scheduling from measured narration cues."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final

from app.deliverables.jobs.policy import VIDEO_SPEC

from .contracts import (
    CreativeVideoProject,
    RuntimeAudioTrack,
    RuntimeNarrationCue,
    SampleFrame,
    VideoRenderInput,
)

WIDTH: Final = 1920
HEIGHT: Final = 1080
FPS: Final = 30
TARGET_MAX_FRAMES: Final = VIDEO_SPEC.max_duration_seconds * FPS
HARD_MAX_FRAMES: Final = VIDEO_SPEC.hard_max_duration_seconds * FPS
WORDS_PER_SECOND: Final = 2.5


@dataclass(frozen=True, slots=True)
class NarrationTarget:
    cue_id: str
    target_seconds: float
    target_words: int


class VideoTimelineDurationError(ValueError):
    """Measured narration exceeds the trusted hard duration limit."""

    def __init__(
        self,
        *,
        compiled_frames: int,
        suggested_narration_targets: tuple[NarrationTarget, ...],
    ) -> None:
        self.max_frames = HARD_MAX_FRAMES
        self.compiled_frames = compiled_frames
        self.overflow_frames = compiled_frames - self.max_frames
        self.suggested_narration_targets = suggested_narration_targets
        super().__init__(
            f"compiled video exceeds the {VIDEO_SPEC.hard_max_duration_seconds}-second "
            f"limit by {self.overflow_frames} frames"
        )


@dataclass(frozen=True, slots=True)
class CueTimeline:
    duration_in_frames: int
    narration_cues: tuple[RuntimeNarrationCue, ...]
    audio_tracks: tuple[RuntimeAudioTrack, ...]


def _neutral_sample_frames(
    timeline: CueTimeline,
    declared: Sequence[SampleFrame | Mapping[str, object]],
) -> tuple[SampleFrame, ...]:
    """Sample temporal coverage without treating narration cues as scenes."""

    reasons: dict[int, str] = {0: "first-content"}
    last_frame = timeline.duration_in_frames - 1
    reasons[last_frame] = "last-content"
    for cue in timeline.narration_cues:
        reasons.setdefault(cue.start_frame, f"cue-start:{cue.cue_id}")
        reasons.setdefault(
            cue.start_frame + cue.duration_in_frames - 1,
            f"cue-end:{cue.cue_id}",
        )
    for position in range(1, 6):
        frame = round(last_frame * position / 6)
        reasons.setdefault(frame, f"even:{position}/6")
    for item in declared:
        sample = (
            item if isinstance(item, SampleFrame) else SampleFrame.model_validate(item)
        )
        reasons[sample.frame] = sample.reason
    return tuple(
        SampleFrame(frame=frame, reason=reason)
        for frame, reason in sorted(reasons.items())
    )


def _value(item: object, name: str) -> object:
    if isinstance(item, Mapping):
        try:
            return item[name]
        except KeyError:
            raise ValueError(f"measured narration is missing {name!r}") from None
    try:
        return getattr(item, name)
    except AttributeError:
        raise ValueError(f"measured narration is missing {name!r}") from None


def _audio_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("measured narration audio must be a non-empty path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or ".." in path.parts
        or "\x00" in value
        or ":" in path.parts[0]
    ):
        raise ValueError("measured narration audio must be a confined public path")
    return value


def _measured_by_cue(
    narration: Sequence[object],
) -> dict[str, tuple[str, float]]:
    measured: dict[str, tuple[str, float]] = {}
    for item in narration:
        cue_id = _value(item, "cue_id")
        duration = _value(item, "duration_seconds")
        if not isinstance(cue_id, str):
            raise ValueError("measured narration cue_id must be a string")
        if cue_id in measured:
            raise ValueError("measured narration cue IDs must be unique")
        if isinstance(duration, bool) or not isinstance(duration, int | float):
            raise ValueError("measured narration duration must be numeric")
        seconds = float(duration)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("measured narration duration must be positive and finite")
        measured[cue_id] = (_audio_path(_value(item, "audio")), seconds)
    return measured


def _repair_targets(
    cue_ids: Sequence[str], audio_frames: Sequence[int]
) -> tuple[NarrationTarget, ...]:
    total = sum(audio_frames)
    remaining = TARGET_MAX_FRAMES
    targets: list[NarrationTarget] = []
    for index, (cue_id, frames) in enumerate(
        zip(cue_ids, audio_frames, strict=True)
    ):
        target_frames = (
            remaining
            if index == len(cue_ids) - 1
            else TARGET_MAX_FRAMES * frames // total
        )
        remaining -= target_frames
        target_seconds = target_frames / FPS
        targets.append(
            NarrationTarget(
                cue_id=cue_id,
                target_seconds=target_seconds,
                target_words=max(1, math.floor(target_seconds * WORDS_PER_SECOND)),
            )
        )
    return tuple(targets)


def compile_video_timeline(
    project: CreativeVideoProject,
    narration: Sequence[object],
) -> CueTimeline:
    """Schedule measured cues sequentially without creating visual containers."""

    measured = _measured_by_cue(narration)
    cue_ids = [cue.cue_id for cue in project.narration_cues]
    expected = set(cue_ids)
    if set(measured) != expected:
        raise ValueError(
            "narration coverage mismatch; "
            f"missing={sorted(expected - set(measured))}, "
            f"extra={sorted(set(measured) - expected)}"
        )

    audio_frames = [math.ceil(measured[cue_id][1] * FPS) for cue_id in cue_ids]
    duration_in_frames = sum(audio_frames)
    if duration_in_frames > HARD_MAX_FRAMES:
        raise VideoTimelineDurationError(
            compiled_frames=duration_in_frames,
            suggested_narration_targets=_repair_targets(cue_ids, audio_frames),
        )

    cues: list[RuntimeNarrationCue] = []
    tracks: list[RuntimeAudioTrack] = []
    start_frame = 0
    for cue_id, frames in zip(cue_ids, audio_frames, strict=True):
        cues.append(
            RuntimeNarrationCue(
                cue_id=cue_id,
                start_frame=start_frame,
                duration_in_frames=frames,
            )
        )
        tracks.append(
            RuntimeAudioTrack(
                cue_id=cue_id,
                src=measured[cue_id][0],
                start_frame=start_frame,
                duration_in_frames=frames,
            )
        )
        start_frame += frames
    return CueTimeline(
        duration_in_frames=duration_in_frames,
        narration_cues=tuple(cues),
        audio_tracks=tuple(tracks),
    )


def build_video_render_input(
    project: CreativeVideoProject,
    narration: Sequence[object],
    *,
    build_id: str,
    selected_capability_ids: Sequence[str] = (),
    sample_frames: Sequence[SampleFrame | Mapping[str, object]] = (),
    watermark: bool = True,
    seed: str | None = None,
) -> VideoRenderInput:
    """Build the exact trusted runtime input from content and measured audio."""

    timeline = compile_video_timeline(project, narration)
    normalized_capability_ids = tuple(sorted(selected_capability_ids))
    normalized_samples = _neutral_sample_frames(timeline, sample_frames)
    return VideoRenderInput(
        build_id=build_id,
        max_duration_seconds=VIDEO_SPEC.hard_max_duration_seconds,
        duration_in_frames=timeline.duration_in_frames,
        selected_capability_ids=normalized_capability_ids,
        narration_cues=timeline.narration_cues,
        audio_tracks=timeline.audio_tracks,
        assets=project.assets,
        sample_frames=normalized_samples,
        watermark=watermark,
        seed=seed
        or hashlib.sha256(
            (
                build_id
                + "\0"
                + "\0".join(cue.cue_id for cue in project.narration_cues)
            ).encode()
        ).hexdigest(),
    )
