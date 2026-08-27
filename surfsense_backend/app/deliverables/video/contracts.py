"""Closed content and trusted runtime contracts for queued video rendering."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.deliverables.jobs.policy import VIDEO_SPEC
from app.sandbox.capabilities.schema import CapabilityId

VIDEO_SCHEMA_VERSION = 1
VIDEO_FPS = 30
VIDEO_HARD_MAX_FRAMES = VIDEO_SPEC.hard_max_duration_seconds * VIDEO_FPS
_SOURCE_PATH = re.compile(r"^[A-Za-z0-9_./-]+\.(?:ts|tsx)$")
CueId = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
]
ReferenceId = Annotated[
    str, Field(min_length=1, max_length=96, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
]


class StrictVideoModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _confined_path(value: str, *, label: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or ".." in path.parts
        or "\x00" in value
        or not path.parts
        or ":" in path.parts[0]
    ):
        raise ValueError(f"{label} must be a confined relative path")
    return value


class NarrationCue(StrictVideoModel):
    cue_id: CueId
    text: Annotated[str, Field(min_length=1, max_length=8000)]

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("narration cue text must not be empty")
        return normalized


class SourceFile(StrictVideoModel):
    path: Annotated[str, Field(min_length=1, max_length=512)]
    source: Annotated[str, Field(min_length=1, max_length=200_000)]

    @field_validator("path")
    @classmethod
    def confined_source_path(cls, value: str) -> str:
        confined = _confined_path(value, label="source file path")
        if _SOURCE_PATH.fullmatch(confined) is None:
            raise ValueError("source files must be TypeScript or TSX")
        return confined


AssetKind = Literal["image", "video", "audio", "svg"]


class AssetReference(StrictVideoModel):
    id: ReferenceId
    path: Annotated[str, Field(min_length=1, max_length=512)]
    kind: AssetKind

    @field_validator("path")
    @classmethod
    def confined_asset_path(cls, value: str) -> str:
        return _confined_path(value, label="asset path")


class CreativeVideoProject(StrictVideoModel):
    """The sole model-authored video contract."""

    narration_cues: Annotated[
        tuple[NarrationCue, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_narration_cues),
    ]
    language: Annotated[str | None, Field(min_length=1, max_length=64)] = None
    source_files: Annotated[
        tuple[SourceFile, ...], Field(min_length=1, max_length=32)
    ]
    assets: Annotated[tuple[AssetReference, ...], Field(max_length=64)] = ()

    @model_validator(mode="after")
    def identities_and_entrypoint_are_closed(self) -> CreativeVideoProject:
        cue_ids = [cue.cue_id for cue in self.narration_cues]
        source_paths = [source.path for source in self.source_files]
        asset_ids = [asset.id for asset in self.assets]
        asset_paths = [asset.path for asset in self.assets]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("narration cue IDs must be unique")
        if len(source_paths) != len(set(source_paths)):
            raise ValueError("source file paths must be unique")
        if sum(len(source.source.encode()) for source in self.source_files) > 256 * 1024:
            raise ValueError("source package exceeds 262144 bytes")
        if "JobComposition.tsx" not in source_paths:
            raise ValueError("source files must include JobComposition.tsx")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("asset IDs must be unique")
        if len(asset_paths) != len(set(asset_paths)):
            raise ValueError("asset paths must be unique")
        return self


class RuntimeNarrationCue(StrictVideoModel):
    cue_id: CueId
    start_frame: Annotated[int, Field(ge=0)]
    duration_in_frames: Annotated[int, Field(gt=0)]


class RuntimeAudioTrack(StrictVideoModel):
    cue_id: CueId
    src: Annotated[str, Field(min_length=1, max_length=512)]
    start_frame: Annotated[int, Field(ge=0)]
    duration_in_frames: Annotated[int, Field(gt=0)]
    volume: Annotated[float, Field(ge=0, le=2)] = 1

    @field_validator("src")
    @classmethod
    def confined_src(cls, value: str) -> str:
        return _confined_path(value, label="audio source")


class SampleFrame(StrictVideoModel):
    frame: Annotated[int, Field(ge=0)]
    reason: Annotated[str, Field(min_length=1, max_length=128)]


class VideoRenderInput(StrictVideoModel):
    """Exact Python mirror of the sole trusted runtime input schema."""

    schema_version: Literal[1] = VIDEO_SCHEMA_VERSION
    build_id: Annotated[str, Field(min_length=8, max_length=128)]
    fps: Literal[30] = VIDEO_FPS
    max_duration_seconds: Annotated[int, Field(gt=0)]
    width: Literal[1920] = 1920
    height: Literal[1080] = 1080
    duration_in_frames: Annotated[int, Field(ge=1, le=VIDEO_HARD_MAX_FRAMES)]
    selected_capability_ids: Annotated[
        tuple[CapabilityId, ...], Field(max_length=100)
    ] = ()
    narration_cues: Annotated[
        tuple[RuntimeNarrationCue, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_narration_cues),
    ]
    audio_tracks: Annotated[
        tuple[RuntimeAudioTrack, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_narration_cues),
    ]
    assets: Annotated[tuple[AssetReference, ...], Field(max_length=64)] = ()
    sample_frames: Annotated[tuple[SampleFrame, ...], Field(max_length=64)] = ()
    watermark: bool = True
    seed: Annotated[str, Field(min_length=1, max_length=128)]

    @model_validator(mode="after")
    def references_are_closed_and_bounded(self) -> VideoRenderInput:
        if self.max_duration_seconds != VIDEO_SPEC.hard_max_duration_seconds:
            raise ValueError("render duration policy does not match the backend")
        if self.duration_in_frames > self.max_duration_seconds * self.fps:
            raise ValueError("video duration exceeds the configured hard limit")
        if len(self.selected_capability_ids) != len(set(self.selected_capability_ids)):
            raise ValueError("selected capability IDs must be unique")

        cue_ids: list[str] = []
        expected_start = 0
        intervals: dict[str, tuple[int, int]] = {}
        for cue in self.narration_cues:
            if cue.start_frame != expected_start:
                raise ValueError("narration cues must be sequential and gap-free")
            end = cue.start_frame + cue.duration_in_frames
            if end > self.duration_in_frames:
                raise ValueError(f"narration cue {cue.cue_id!r} exceeds video duration")
            cue_ids.append(cue.cue_id)
            intervals[cue.cue_id] = (cue.start_frame, cue.duration_in_frames)
            expected_start = end
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("runtime narration cue IDs must be unique")
        if expected_start != self.duration_in_frames:
            raise ValueError("video duration must equal the scheduled narration duration")

        track_ids = [track.cue_id for track in self.audio_tracks]
        if track_ids != cue_ids:
            raise ValueError("audio tracks must match narration cue order and coverage")
        for track in self.audio_tracks:
            if (track.start_frame, track.duration_in_frames) != intervals[track.cue_id]:
                raise ValueError(
                    f"audio track {track.cue_id!r} must match its narration cue"
                )

        asset_ids = [asset.id for asset in self.assets]
        asset_paths = [asset.path for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)) or len(asset_paths) != len(
            set(asset_paths)
        ):
            raise ValueError("runtime assets must have unique IDs and paths")
        sample_values = [sample.frame for sample in self.sample_frames]
        if len(sample_values) != len(set(sample_values)):
            raise ValueError("sample frames must be unique")
        if any(frame >= self.duration_in_frames for frame in sample_values):
            raise ValueError("sample frame exceeds video duration")
        return self


__all__ = [
    "AssetKind",
    "AssetReference",
    "CreativeVideoProject",
    "NarrationCue",
    "RuntimeAudioTrack",
    "RuntimeNarrationCue",
    "SampleFrame",
    "SourceFile",
    "VideoRenderInput",
]
