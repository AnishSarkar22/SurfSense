"""Strict declarative contracts for capability-authored video rendering."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from app.deliverables.jobs.policy import VIDEO_SPEC
from app.sandbox.capabilities.schema import (
    CapabilityCandidate,
    CapabilityDisclosure,
    CapabilityId,
)

VIDEO_SCHEMA_VERSION = 1
BeatId = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
]
LayerId = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
]
CapabilitySlot = Annotated[str, Field(pattern=r"^capability-[0-9]{2}$")]


class StrictVideoModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class VisualIntent(StrictVideoModel):
    beat_id: BeatId
    description: Annotated[str, Field(min_length=1, max_length=1000)]
    categories: Annotated[tuple[str, ...], Field(max_length=8)] = ()
    tags: Annotated[tuple[str, ...], Field(max_length=16)] = ()
    vibe: Annotated[tuple[str, ...], Field(max_length=8)] = ()
    avoid: Annotated[tuple[str, ...], Field(max_length=8)] = ()
    target_duration_seconds: Annotated[float | None, Field(gt=0, le=180)] = None


class CreativeOutline(StrictVideoModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    objective: Annotated[str, Field(min_length=1, max_length=1000)]
    audience: Annotated[str, Field(min_length=1, max_length=500)]
    language: Annotated[str | None, Field(max_length=64)] = None
    visual_intents: Annotated[
        tuple[VisualIntent, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_beats),
    ]

    @model_validator(mode="after")
    def unique_beats(self) -> CreativeOutline:
        ids = [intent.beat_id for intent in self.visual_intents]
        if len(ids) != len(set(ids)):
            raise ValueError("outline beat IDs must be unique")
        return self


class Bounds(StrictVideoModel):
    x: Annotated[int, Field(ge=0, lt=1920)]
    y: Annotated[int, Field(ge=0, lt=1080)]
    width: Annotated[int, Field(gt=0, le=1920)]
    height: Annotated[int, Field(gt=0, le=1080)]


class LayerTiming(StrictVideoModel):
    start_frame: Annotated[int, Field(ge=0)] = 0
    end_frame: Annotated[int | None, Field(gt=0)] = None

    @model_validator(mode="after")
    def ordered(self) -> LayerTiming:
        if self.end_frame is not None and self.end_frame <= self.start_frame:
            raise ValueError("layer end_frame must be after start_frame")
        return self


class TextLayer(StrictVideoModel):
    type: Literal["text"]
    id: LayerId
    bounds: Bounds
    timing: LayerTiming = LayerTiming()
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    font_id: CapabilityId
    font_size: Annotated[int, Field(ge=12, le=240)]
    color: Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")]
    safe_margin: bool = True


class ShapeLayer(StrictVideoModel):
    type: Literal["shape"]
    id: LayerId
    bounds: Bounds
    timing: LayerTiming = LayerTiming()
    shape: Literal["rectangle", "ellipse", "line"]
    fill: Annotated[str, Field(min_length=1, max_length=128)]
    safe_margin: bool = False


class MediaLayer(StrictVideoModel):
    type: Literal["media"]
    id: LayerId
    bounds: Bounds
    timing: LayerTiming = LayerTiming()
    asset_id: Annotated[str, Field(min_length=1, max_length=96)]
    fit: Literal["contain", "cover", "fill"] = "cover"
    safe_margin: bool = False


class CapabilityLayer(StrictVideoModel):
    type: Literal["capability"]
    id: LayerId
    bounds: Bounds
    timing: LayerTiming = LayerTiming()
    capability_id: CapabilityId
    props: dict[str, JsonValue] = Field(default_factory=dict)
    generated_elements: Annotated[int, Field(ge=1, le=100)] = 1
    safe_margin: bool = True


class AuthoredTextLayer(StrictVideoModel):
    type: Literal["text"]
    id: LayerId
    bounds: Bounds
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    font_id: CapabilityId
    font_size: Annotated[int, Field(ge=12, le=240)]
    color: Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")]
    safe_margin: bool = True


class AuthoredShapeLayer(StrictVideoModel):
    type: Literal["shape"]
    id: LayerId
    bounds: Bounds
    shape: Literal["rectangle", "ellipse", "line"]
    fill: Annotated[str, Field(min_length=1, max_length=128)]
    safe_margin: bool = False


class AuthoredMediaLayer(StrictVideoModel):
    type: Literal["media"]
    id: LayerId
    bounds: Bounds
    asset_id: Annotated[str, Field(min_length=1, max_length=96)]
    fit: Literal["contain", "cover", "fill"] = "cover"
    safe_margin: bool = False


class AuthoredCapabilityLayer(StrictVideoModel):
    type: Literal["capability"]
    id: LayerId
    bounds: Bounds
    capability_slot: CapabilitySlot
    props: dict[str, JsonValue] = Field(default_factory=dict)
    generated_elements: Annotated[int, Field(ge=1, le=100)] = 1
    safe_margin: bool = True


AuthoredDeclarativeLayer = Annotated[
    AuthoredTextLayer
    | AuthoredShapeLayer
    | AuthoredMediaLayer
    | AuthoredCapabilityLayer,
    Field(discriminator="type"),
]


DeclarativeLayer = Annotated[
    TextLayer | ShapeLayer | MediaLayer | CapabilityLayer,
    Field(discriminator="type"),
]


class AssetKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SVG = "svg"


class AssetReference(StrictVideoModel):
    id: Annotated[str, Field(min_length=1, max_length=96)]
    kind: AssetKind
    path: Annotated[str, Field(min_length=1, max_length=512)]
    alt: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("path")
    @classmethod
    def confined_public_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\x00" in value:
            raise ValueError("asset path must be a confined relative public path")
        return value


class TransitionSelection(StrictVideoModel):
    capability_id: CapabilityId
    duration_frames: Annotated[int, Field(gt=0, le=120)]
    props: dict[str, JsonValue] = Field(default_factory=dict)


class AuthoredTransitionSelection(StrictVideoModel):
    capability_slot: CapabilitySlot
    props: dict[str, JsonValue] = Field(default_factory=dict)


class VideoStyle(StrictVideoModel):
    background: Annotated[str, Field(min_length=1, max_length=128)] = "#0B1020"
    primary_font_id: CapabilityId
    secondary_font_id: CapabilityId | None = None
    palette: Annotated[tuple[str, ...], Field(min_length=1, max_length=8)]


class AuthoredVideoStyle(StrictVideoModel):
    background: Annotated[str, Field(min_length=1, max_length=128)] = "#0B1020"
    primary_font_id: CapabilityId
    secondary_font_id: CapabilityId | None = None
    palette: Annotated[tuple[str, ...], Field(min_length=1, max_length=8)]


class Pacing(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DELIBERATE = "deliberate"


class AuthoredVideoBeat(StrictVideoModel):
    beat_id: BeatId
    utterance_id: Annotated[
        str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    ]
    narration: Annotated[str, Field(min_length=2, max_length=8000)]
    pacing: Pacing = Pacing.STANDARD
    layers: Annotated[
        tuple[AuthoredDeclarativeLayer, ...], Field(min_length=1, max_length=40)
    ]
    transition_to_next: AuthoredTransitionSelection | None = None

    @field_validator("narration")
    @classmethod
    def complete_sentences(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if normalized[-1] not in ".!?\u3002\uff01\uff1f":
            raise ValueError("narration must contain complete sentences")
        return normalized

    @model_validator(mode="after")
    def unique_layers(self) -> AuthoredVideoBeat:
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError(f"layer IDs must be unique within beat {self.beat_id!r}")
        return self


class VideoBeat(StrictVideoModel):
    beat_id: BeatId
    utterance_id: Annotated[
        str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    ]
    narration: Annotated[str, Field(min_length=2, max_length=8000)]
    layers: Annotated[tuple[DeclarativeLayer, ...], Field(min_length=1, max_length=40)]
    min_duration_frames: Annotated[int, Field(ge=1, le=5400)] = 1
    transition_to_next: TransitionSelection | None = None
    seed: Annotated[int | None, Field(ge=0, le=2**32 - 1)] = None

    @field_validator("narration")
    @classmethod
    def complete_sentences(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if normalized[-1] not in ".!?\u3002\uff01\uff1f":
            raise ValueError("narration must contain complete sentences")
        return normalized

    @model_validator(mode="after")
    def unique_layers(self) -> VideoBeat:
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError(f"layer IDs must be unique within beat {self.beat_id!r}")
        return self


class VideoPlan(StrictVideoModel):
    schema_version: Literal[1] = VIDEO_SCHEMA_VERSION
    build_id: Annotated[str, Field(min_length=8, max_length=128)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    language: Annotated[str | None, Field(max_length=64)] = None
    selected_capability_ids: Annotated[
        tuple[CapabilityId, ...], Field(min_length=1, max_length=64)
    ]
    style: VideoStyle
    assets: Annotated[tuple[AssetReference, ...], Field(max_length=64)] = ()
    beats: Annotated[
        tuple[VideoBeat, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_beats),
    ]

    @model_validator(mode="after")
    def references_are_closed(self) -> VideoPlan:
        beat_ids = [beat.beat_id for beat in self.beats]
        utterance_ids = [beat.utterance_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("video beat IDs must be unique")
        if len(utterance_ids) != len(set(utterance_ids)):
            raise ValueError("video utterance IDs must be unique")
        if len(self.selected_capability_ids) != len(set(self.selected_capability_ids)):
            raise ValueError("selected capability IDs must be unique")

        selected = set(self.selected_capability_ids)
        referenced = {
            self.style.primary_font_id,
            *(
                (self.style.secondary_font_id,)
                if self.style.secondary_font_id is not None
                else ()
            ),
        }
        asset_ids = {asset.id for asset in self.assets}
        if len(asset_ids) != len(self.assets):
            raise ValueError("asset IDs must be unique")
        for beat in self.beats:
            if beat.transition_to_next is not None:
                referenced.add(beat.transition_to_next.capability_id)
            for layer in beat.layers:
                if isinstance(layer, TextLayer):
                    referenced.add(layer.font_id)
                elif isinstance(layer, CapabilityLayer):
                    referenced.add(layer.capability_id)
                elif isinstance(layer, MediaLayer) and layer.asset_id not in asset_ids:
                    raise ValueError(f"unknown asset ID: {layer.asset_id!r}")
        missing = referenced - selected
        if missing:
            raise ValueError(
                f"referenced capability IDs are not selected: {sorted(missing)}"
            )
        if self.beats[-1].transition_to_next is not None:
            raise ValueError("the final beat cannot transition to a following beat")
        return self


class AuthoredVideoPlan(StrictVideoModel):
    """LLM-facing plan; compiler-owned identity and timing are intentionally absent."""

    title: Annotated[str, Field(min_length=1, max_length=200)]
    language: Annotated[str | None, Field(max_length=64)] = None
    style: AuthoredVideoStyle
    assets: Annotated[tuple[AssetReference, ...], Field(max_length=64)] = ()
    beats: Annotated[
        tuple[AuthoredVideoBeat, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_beats),
    ]

    @model_validator(mode="after")
    def references_are_unique(self) -> AuthoredVideoPlan:
        beat_ids = [beat.beat_id for beat in self.beats]
        utterance_ids = [beat.utterance_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("video beat IDs must be unique")
        if len(utterance_ids) != len(set(utterance_ids)):
            raise ValueError("video utterance IDs must be unique")
        if self.beats[-1].transition_to_next is not None:
            raise ValueError("the final beat cannot transition to a following beat")
        return self


class NarrationRewriteBeat(StrictVideoModel):
    beat_id: BeatId
    utterance_id: Annotated[
        str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    ]
    narration: Annotated[str, Field(min_length=2, max_length=8000)]

    @field_validator("narration")
    @classmethod
    def complete_sentences(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if normalized[-1] not in ".!?\u3002\uff01\uff1f":
            raise ValueError("narration must contain complete sentences")
        return normalized


class NarrationRewrite(StrictVideoModel):
    """Narration-only repair; visual and timing fields are intentionally absent."""

    beats: Annotated[
        tuple[NarrationRewriteBeat, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_beats),
    ]

    @model_validator(mode="after")
    def unique_identities(self) -> NarrationRewrite:
        beat_ids = [beat.beat_id for beat in self.beats]
        utterance_ids = [beat.utterance_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)) or len(utterance_ids) != len(
            set(utterance_ids)
        ):
            raise ValueError("narration rewrite identities must be unique")
        return self


class TimelineLayer(StrictVideoModel):
    beat_id: BeatId
    layer: DeclarativeLayer
    from_frame: Annotated[int, Field(ge=0)]
    to_frame: Annotated[int, Field(gt=0)]


class TimelineBeat(StrictVideoModel):
    beat_id: BeatId
    utterance_id: str
    from_frame: Annotated[int, Field(ge=0)]
    to_frame: Annotated[int, Field(gt=0)]
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)]


class TimelineTransition(StrictVideoModel):
    capability_id: CapabilityId
    from_beat_id: BeatId
    to_beat_id: BeatId
    from_frame: Annotated[int, Field(ge=0)]
    to_frame: Annotated[int, Field(gt=0)]
    props: dict[str, JsonValue] = Field(default_factory=dict)


class NarrationTrack(StrictVideoModel):
    beat_id: BeatId
    utterance_id: str
    audio: Annotated[str, Field(min_length=1, max_length=512)]
    from_frame: Annotated[int, Field(ge=0)]
    to_frame: Annotated[int, Field(gt=0)]
    duration_seconds: Annotated[float, Field(gt=0)]


class VideoTimeline(StrictVideoModel):
    width: Literal[1920] = 1920
    height: Literal[1080] = 1080
    fps: Literal[30] = 30
    duration_frames: Annotated[int, Field(gt=0, le=5400)]
    beats: tuple[TimelineBeat, ...]
    layers: tuple[TimelineLayer, ...]
    transitions: tuple[TimelineTransition, ...]
    narration: tuple[NarrationTrack, ...]


class RenderFilter(StrictVideoModel):
    blur: Annotated[float, Field(ge=0, le=100)] = 0
    brightness: Annotated[float, Field(ge=0, le=4)] = 1
    contrast: Annotated[float, Field(ge=0, le=4)] = 1
    saturate: Annotated[float, Field(ge=0, le=4)] = 1


class RenderKeyframe(StrictVideoModel):
    frame: Annotated[int, Field(ge=0)]
    opacity: Annotated[float | None, Field(ge=0, le=1)] = None
    x: float | None = None
    y: float | None = None
    scale: Annotated[float | None, Field(gt=0, le=20)] = None


class RenderPlacement(StrictVideoModel):
    id: LayerId
    from_: Annotated[int, Field(ge=0, alias="from")] = 0
    duration_in_frames: Annotated[int, Field(gt=0)]
    x: float = 0
    y: float = 0
    width: Annotated[float, Field(gt=0, le=1920)] = 1920
    height: Annotated[float, Field(gt=0, le=1080)] = 1080
    opacity: Annotated[float, Field(ge=0, le=1)] = 1
    rotation: float = 0
    scale: Annotated[float, Field(gt=0, le=20)] = 1
    z_index: Annotated[int, Field(ge=-100, le=100)] = 0
    filter: RenderFilter | None = None
    keyframes: Annotated[tuple[RenderKeyframe, ...], Field(max_length=20)] = ()


class RenderTextLayer(RenderPlacement):
    type: Literal["text", "rich_text"]
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    color: Annotated[str, Field(min_length=1, max_length=128)] = "#f8fafc"
    font_id: CapabilityId = "font.inter"
    font_size: Annotated[float, Field(ge=8, le=300)] = 72
    font_weight: Annotated[int, Field(ge=100, le=900)] = 500
    align: Literal["left", "center", "right"] = "left"


class RenderShapeLayer(RenderPlacement):
    type: Literal["shape"]
    shape: Literal["rectangle", "ellipse", "line"] = "rectangle"
    fill: Annotated[str, Field(min_length=1, max_length=128)] = "#0f172a"
    stroke: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    stroke_width: Annotated[float, Field(ge=0, le=100)] = 0
    radius: Annotated[float, Field(ge=0, le=960)] = 0
    gradient_to: Annotated[str | None, Field(min_length=1, max_length=128)] = None


class RenderMediaLayer(RenderPlacement):
    type: Literal["image", "video"]
    src: Annotated[str, Field(min_length=1, max_length=512)]
    fit: Literal["contain", "cover", "fill"] = "cover"
    muted: bool = True

    @field_validator("src")
    @classmethod
    def confined_src(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\x00" in value
            or ":" in path.parts[0]
        ):
            raise ValueError(
                "asset path must be relative to the staged public directory"
            )
        return value


class RenderSvgLayer(RenderPlacement):
    type: Literal["svg", "icon"]
    path: Annotated[str, Field(min_length=1, max_length=20_000)]
    view_box: Annotated[str, Field(min_length=1, max_length=100)] = "0 0 24 24"
    fill: Annotated[str, Field(min_length=1, max_length=128)] = "currentColor"
    stroke: Annotated[str | None, Field(min_length=1, max_length=128)] = None


class RenderChartLayer(RenderPlacement):
    type: Literal["chart"]
    chart: Literal["bar", "line", "metric_grid"]
    values: Annotated[tuple[float, ...], Field(min_length=1, max_length=100)]
    labels: Annotated[
        tuple[Annotated[str, Field(max_length=48)], ...], Field(max_length=100)
    ] = ()
    color: Annotated[str, Field(min_length=1, max_length=128)] = "#38bdf8"


class RenderCodeLayer(RenderPlacement):
    type: Literal["code"]
    code: Annotated[str, Field(min_length=1, max_length=12_000)]
    language: Annotated[str, Field(max_length=40)] = "text"
    highlight_lines: Annotated[
        tuple[Annotated[int, Field(gt=0)], ...], Field(max_length=50)
    ] = ()


class RenderConnectorLayer(RenderPlacement):
    type: Literal["connector"]
    x2: float
    y2: float
    color: Annotated[str, Field(min_length=1, max_length=128)] = "#94a3b8"
    stroke_width: Annotated[float, Field(gt=0, le=40)] = 4
    arrow: bool = False


class RenderAudioVisualizationLayer(RenderPlacement):
    type: Literal["audio_visualization"]
    samples: Annotated[
        tuple[Annotated[float, Field(ge=0, le=1)], ...],
        Field(min_length=2, max_length=512),
    ]
    color: Annotated[str, Field(min_length=1, max_length=128)] = "#38bdf8"
    bars: Annotated[int, Field(ge=2, le=128)] = 48


class RenderRepeatedLayer(RenderPlacement):
    type: Literal["repeated"]
    count: Annotated[int, Field(ge=1, le=100)]
    columns: Annotated[int, Field(ge=1, le=20)] = 5
    gap: Annotated[float, Field(ge=0, le=200)] = 16
    fill: Annotated[str, Field(min_length=1, max_length=128)] = "#334155"
    radius: Annotated[float, Field(ge=0, le=200)] = 12


RenderCoreLeaf = Annotated[
    RenderTextLayer
    | RenderShapeLayer
    | RenderMediaLayer
    | RenderSvgLayer
    | RenderChartLayer
    | RenderCodeLayer
    | RenderConnectorLayer
    | RenderAudioVisualizationLayer
    | RenderRepeatedLayer,
    Field(discriminator="type"),
]


class RenderGroupLayer(RenderPlacement):
    type: Literal["group"]
    layout: Literal["free", "row", "column", "grid"] = "free"
    gap: Annotated[float, Field(ge=0, le=200)] = 0
    clip: bool = False
    children: Annotated[tuple[RenderCoreLeaf, ...], Field(max_length=50)]


class RenderCapabilityLayer(RenderPlacement):
    type: Literal["component"]
    capability_id: CapabilityId
    props: dict[str, JsonValue] = Field(default_factory=dict)


RenderLayer = RenderCoreLeaf | RenderGroupLayer | RenderCapabilityLayer


class RenderBeat(StrictVideoModel):
    id: Annotated[str, Field(min_length=1, max_length=100)]
    utterance_id: Annotated[str, Field(min_length=1, max_length=100)]
    start_frame: Annotated[int, Field(ge=0)]
    duration_in_frames: Annotated[int, Field(gt=0)]
    background: Annotated[str, Field(min_length=1, max_length=128)] = "#020617"
    layers: Annotated[tuple[RenderLayer, ...], Field(max_length=100)]

    @model_validator(mode="after")
    def unique_layer_ids(self) -> RenderBeat:
        ids = [layer.id for layer in self.layers]
        if len(ids) != len(set(ids)):
            raise ValueError(f"layer IDs must be unique within beat {self.id!r}")
        return self


class RenderTransition(StrictVideoModel):
    capability_id: CapabilityId
    from_beat_id: Annotated[str, Field(min_length=1, max_length=100)]
    to_beat_id: Annotated[str, Field(min_length=1, max_length=100)]
    start_frame: Annotated[int, Field(ge=0)]
    duration_in_frames: Annotated[int, Field(ge=1, le=120)]
    props: dict[str, JsonValue] = Field(default_factory=dict)


class RenderAudioTrack(StrictVideoModel):
    utterance_id: Annotated[str, Field(min_length=1, max_length=100)]
    src: Annotated[str, Field(min_length=1, max_length=512)]
    start_frame: Annotated[int, Field(ge=0)]
    duration_in_frames: Annotated[int, Field(gt=0)]
    volume: Annotated[float, Field(ge=0, le=2)] = 1

    _confined_src = field_validator("src")(RenderMediaLayer.confined_src.__func__)


class RenderCaption(StrictVideoModel):
    text: str
    start_ms: Annotated[float, Field(ge=0, alias="startMs")]
    end_ms: Annotated[float, Field(gt=0, alias="endMs")]
    timestamp_ms: Annotated[float | None, Field(alias="timestampMs")]
    confidence: Annotated[float | None, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def ordered(self) -> RenderCaption:
        if self.end_ms <= self.start_ms:
            raise ValueError("caption endMs must exceed startMs")
        return self


class VideoRenderInput(StrictVideoModel):
    """Exact Python mirror of the baked renderer's VideoRenderInputSchema."""

    schema_version: Literal[1] = VIDEO_SCHEMA_VERSION
    build_id: Annotated[str, Field(min_length=8, max_length=128)]
    skill_version: Annotated[str, Field(min_length=1, max_length=128)]
    fps: Literal[30] = 30
    width: Literal[1920] = 1920
    height: Literal[1080] = 1080
    duration_in_frames: Annotated[int, Field(ge=1, le=5400)]
    selected_capability_ids: Annotated[
        tuple[CapabilityId, ...], Field(min_length=1, max_length=100)
    ]
    beats: Annotated[tuple[RenderBeat, ...], Field(min_length=1, max_length=12)]
    transitions: Annotated[tuple[RenderTransition, ...], Field(max_length=11)] = ()
    audio_tracks: Annotated[tuple[RenderAudioTrack, ...], Field(max_length=12)] = ()
    captions: Annotated[tuple[RenderCaption, ...], Field(max_length=2000)] = ()
    watermark: bool = True
    seed: Annotated[str, Field(min_length=1, max_length=128)]

    @model_validator(mode="after")
    def references_are_bounded(self) -> VideoRenderInput:
        selected = set(self.selected_capability_ids)
        for beat in self.beats:
            if beat.start_frame + beat.duration_in_frames > self.duration_in_frames:
                raise ValueError(f"beat {beat.id!r} exceeds video duration")
            for layer in beat.layers:
                capability_id = getattr(layer, "capability_id", None)
                if capability_id is not None and capability_id not in selected:
                    raise ValueError(f"undeclared capability {capability_id!r}")
                if layer.from_ + layer.duration_in_frames > beat.duration_in_frames:
                    raise ValueError(f"layer in beat {beat.id!r} exceeds beat duration")
        for transition in self.transitions:
            if transition.capability_id not in selected:
                raise ValueError(f"undeclared transition {transition.capability_id!r}")
        return self


__all__ = [
    "AssetReference",
    "AuthoredCapabilityLayer",
    "AuthoredDeclarativeLayer",
    "AuthoredMediaLayer",
    "AuthoredShapeLayer",
    "AuthoredTextLayer",
    "AuthoredTransitionSelection",
    "AuthoredVideoBeat",
    "AuthoredVideoPlan",
    "AuthoredVideoStyle",
    "Bounds",
    "CapabilityCandidate",
    "CapabilityDisclosure",
    "CapabilityLayer",
    "CreativeOutline",
    "DeclarativeLayer",
    "MediaLayer",
    "NarrationTrack",
    "Pacing",
    "ShapeLayer",
    "TextLayer",
    "TimelineBeat",
    "TimelineLayer",
    "TimelineTransition",
    "TransitionSelection",
    "VideoBeat",
    "VideoPlan",
    "VideoRenderInput",
    "VideoStyle",
    "VideoTimeline",
    "VisualIntent",
]
