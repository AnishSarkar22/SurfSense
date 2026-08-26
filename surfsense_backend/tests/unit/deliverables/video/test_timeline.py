from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.deliverables.video.contracts import (
    Bounds,
    CapabilityLayer,
    LayerTiming,
    TextLayer,
    TransitionSelection,
    VideoBeat,
    VideoPlan,
    VideoRenderInput,
    VideoStyle,
)
from app.deliverables.video.timeline import (
    VideoTimelineDurationError,
    build_video_render_input,
    compile_video_timeline,
)

pytestmark = pytest.mark.unit


def _plan(*, transition_frames: int = 10, unsafe_x: int = 100) -> VideoPlan:
    return VideoPlan(
        build_id="build-12345678",
        title="Quarterly update",
        selected_capability_ids=(
            "font.inter",
            "video.component.animated-bar-chart",
            "video.transition.whip-pan",
        ),
        style=VideoStyle(
            primary_font_id="font.inter",
            palette=("#101828", "#FFFFFF"),
        ),
        beats=(
            VideoBeat(
                beat_id="opening",
                utterance_id="opening-narration",
                narration="Revenue grew in every region.",
                layers=(
                    CapabilityLayer(
                        type="capability",
                        id="metrics",
                        bounds=Bounds(x=unsafe_x, y=100, width=1200, height=700),
                        capability_id="video.component.animated-bar-chart",
                        props={"data": [12, 18], "labels": ["Q1", "Q2"]},
                        generated_elements=12,
                    ),
                ),
                transition_to_next=TransitionSelection(
                    capability_id="video.transition.whip-pan",
                    duration_frames=transition_frames,
                ),
            ),
            VideoBeat(
                beat_id="close",
                utterance_id="close-narration",
                narration="The team is positioned for durable growth.",
                layers=(
                    TextLayer(
                        type="text",
                        id="headline",
                        bounds=Bounds(x=100, y=100, width=1000, height=300),
                        timing=LayerTiming(start_frame=0),
                        text="Durable growth",
                        font_id="font.inter",
                        font_size=72,
                        color="#FFFFFF",
                    ),
                ),
            ),
        ),
    )


def _narration() -> list[dict[str, object]]:
    return [
        {
            "beat_id": "opening",
            "utterance_id": "opening-narration",
            "audio": "utterance-opening-narration.wav",
            "duration_seconds": 0.5,
        },
        {
            "beat_id": "close",
            "utterance_id": "close-narration",
            "audio": "utterance-close-narration.wav",
            "duration_seconds": 1.0,
        },
    ]


def _without_transition(*, min_duration_frames: int = 1) -> VideoPlan:
    plan = _plan()
    return plan.model_copy(
        update={
            "beats": tuple(
                beat.model_copy(
                    update={
                        "min_duration_frames": min_duration_frames,
                        "transition_to_next": None,
                    }
                )
                for beat in plan.beats
            )
        }
    )


def test_compiler_uses_measured_audio_and_natural_frames_deterministically() -> None:
    first = compile_video_timeline(
        _plan(),
        _narration(),
        capability_natural_frames={
            "video.component.animated-bar-chart": 45,
        },
    )
    second = compile_video_timeline(
        _plan(),
        _narration(),
        capability_natural_frames={
            "video.component.animated-bar-chart": 45,
        },
    )

    assert first == second
    assert (first.width, first.height, first.fps) == (1920, 1080, 30)
    assert first.beats[0].from_frame == 0
    assert first.beats[0].to_frame == 45
    assert first.beats[1].from_frame == 35
    assert first.narration[0].to_frame == 15
    assert first.narration[1].from_frame == 35
    assert first.duration_frames == 65
    assert (first.transitions[0].from_frame, first.transitions[0].to_frame) == (
        35,
        45,
    )

    render_input = build_video_render_input(
        _plan(),
        _narration(),
        skill_version="skill-v1",
        capability_natural_frames={
            "video.component.animated-bar-chart": 45,
        },
    )
    assert render_input.duration_in_frames == first.duration_frames
    assert render_input.beats[0].start_frame == first.beats[0].from_frame
    assert render_input.audio_tracks[1].start_frame == first.narration[1].from_frame
    assert render_input.selected_capability_ids == tuple(
        sorted(render_input.selected_capability_ids)
    )
    document = render_input.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert set(document) == {
        "schema_version",
        "build_id",
        "skill_version",
        "fps",
        "max_duration_seconds",
        "width",
        "height",
        "duration_in_frames",
        "selected_capability_ids",
        "beats",
        "transitions",
        "audio_tracks",
        "captions",
        "watermark",
        "seed",
    }
    assert document["beats"][0] == {
        "id": "opening",
        "utterance_id": "opening-narration",
        "start_frame": 0,
        "duration_in_frames": 45,
        "background": "#0B1020",
        "layers": [
            {
                "id": "metrics",
                "from": 0,
                "duration_in_frames": 45,
                "x": 100.0,
                "y": 100.0,
                "width": 1200.0,
                "height": 700.0,
                "opacity": 1.0,
                "rotation": 0.0,
                "scale": 1.0,
                "z_index": 0,
                "keyframes": [],
                "type": "component",
                "capability_id": "video.component.animated-bar-chart",
                "props": {"data": [12.0, 18.0], "labels": ["Q1", "Q2"]},
            }
        ],
    }
    assert document["transitions"] == [
        {
            "capability_id": "video.transition.whip-pan",
            "from_beat_id": "opening",
            "to_beat_id": "close",
            "start_frame": 35,
            "duration_in_frames": 10,
            "props": {},
        }
    ]
    assert document["audio_tracks"][1] == {
        "utterance_id": "close-narration",
        "src": "utterance-close-narration.wav",
        "start_frame": 35,
        "duration_in_frames": 30,
        "volume": 1.0,
    }
    assert not ({"tsx", "scene", "scenes"} & set(str(document).casefold().split()))


def test_compiler_accepts_the_target_and_hard_frame_limits() -> None:
    measured = _narration()
    measured[0]["duration_seconds"] = 90
    measured[1]["duration_seconds"] = 90

    timeline = compile_video_timeline(_without_transition(), measured)

    assert timeline.duration_frames == 5400

    measured[0]["duration_seconds"] = 105
    measured[1]["duration_seconds"] = 105

    timeline = compile_video_timeline(_without_transition(), measured)

    assert timeline.duration_frames == 6300


@pytest.mark.parametrize("duration_seconds", [180.13, 205.0])
def test_compiler_accepts_measured_narration_headroom(duration_seconds) -> None:
    measured = _narration()
    measured[0]["duration_seconds"] = duration_seconds
    measured[1]["duration_seconds"] = 0.01

    timeline = compile_video_timeline(_without_transition(), measured)

    assert 5400 < timeline.duration_frames <= 6300


def test_render_input_contract_uses_the_hard_frame_limit() -> None:
    document = build_video_render_input(
        _without_transition(),
        _narration(),
        skill_version="skill-v1",
    ).model_dump(by_alias=True)
    document["duration_in_frames"] = 6300

    assert VideoRenderInput.model_validate(document).duration_in_frames == 6300

    document["duration_in_frames"] = 6301
    with pytest.raises(ValidationError):
        VideoRenderInput.model_validate(document)


def test_compiler_removes_discretionary_holds_before_rejecting_duration() -> None:
    timeline = compile_video_timeline(
        _without_transition(min_duration_frames=3000),
        _narration(),
    )

    assert timeline.duration_frames == 45
    assert [beat.to_frame - beat.from_frame for beat in timeline.beats] == [15, 30]


def test_compiler_reports_structured_narration_repair_budgets() -> None:
    measured = _narration()
    measured[0]["duration_seconds"] = 110
    measured[1]["duration_seconds"] = 110

    with pytest.raises(VideoTimelineDurationError) as raised:
        compile_video_timeline(_without_transition(), measured)

    error = raised.value
    assert (error.max_frames, error.compiled_frames, error.overflow_frames) == (
        6300,
        6600,
        300,
    )
    assert [
        (budget.beat_id, budget.max_seconds, budget.max_words)
        for budget in error.suggested_narration_budgets
    ] == [
        ("opening", 90.0, 225),
        ("close", 90.0, 225),
    ]


def test_compiler_rejects_unsafe_bounds_transition_and_narration_gaps() -> None:
    with pytest.raises(ValueError, match="safe margin"):
        compile_video_timeline(_plan(unsafe_x=10), _narration())

    with pytest.raises(ValueError, match="half an adjacent beat"):
        compile_video_timeline(_plan(transition_frames=20), _narration())

    with pytest.raises(ValueError, match="coverage mismatch"):
        compile_video_timeline(_plan(), _narration()[:1])

    too_long = _narration()
    too_long[0]["duration_seconds"] = 211
    with pytest.raises(ValueError, match="210-second"):
        compile_video_timeline(_plan(), too_long)


def test_contract_forbids_generated_code_and_requires_complete_sentences() -> None:
    document = _plan().model_dump()
    document["beats"][0]["tsx"] = "export default function ArbitraryCode() {}"

    with pytest.raises(ValidationError, match="tsx"):
        VideoPlan.model_validate(document)

    beat = _plan().beats[0].model_dump()
    beat["narration"] = "An incomplete fragment"
    with pytest.raises(ValidationError, match="complete sentences"):
        VideoBeat.model_validate(beat)

    schema_text = str(VideoPlan.model_json_schema()).casefold()
    assert "scene" not in schema_text
    assert "slide" not in schema_text
    assert "tsx" not in schema_text
