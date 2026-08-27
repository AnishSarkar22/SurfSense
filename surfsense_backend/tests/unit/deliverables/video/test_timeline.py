from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.deliverables.video.contracts import CreativeVideoProject, VideoRenderInput
from app.deliverables.video.timeline import (
    VideoTimelineDurationError,
    build_video_render_input,
    compile_video_timeline,
)

pytestmark = pytest.mark.unit


def _project() -> CreativeVideoProject:
    return CreativeVideoProject(
        narration_cues=(
            {"cue_id": "opening", "text": "Revenue grew in every region."},
            {"cue_id": "close", "text": "The team is ready for durable growth."},
        ),
        source_files=(
            {
                "path": "JobComposition.tsx",
                "source": "export const JobComposition = () => null;",
            },
        ),
        assets=({"id": "logo", "path": "assets/logo.svg", "kind": "svg"},),
    )


def _narration() -> list[dict[str, object]]:
    return [
        {
            "cue_id": "opening",
            "audio": "narration-opening.wav",
            "duration_seconds": 0.5,
        },
        {
            "cue_id": "close",
            "audio": "narration-close.wav",
            "duration_seconds": 1.01,
        },
    ]


def test_scheduler_uses_measured_audio_sequentially_and_deterministically() -> None:
    first = compile_video_timeline(_project(), _narration())
    second = compile_video_timeline(_project(), _narration())

    assert first == second
    assert first.duration_in_frames == 46
    assert [
        (cue.cue_id, cue.start_frame, cue.duration_in_frames)
        for cue in first.narration_cues
    ] == [("opening", 0, 15), ("close", 15, 31)]
    assert first.audio_tracks[1].start_frame == 15
    assert first.audio_tracks[1].duration_in_frames == 31


def test_builder_emits_the_exact_runtime_interface() -> None:
    render_input = build_video_render_input(
        _project(),
        _narration(),
        build_id="build-12345678",
        selected_capability_ids=("video.component.chart", "font.inter"),
        sample_frames=(
            {"frame": 0, "reason": "first"},
            {"frame": 45, "reason": "final"},
        ),
    )

    document = render_input.model_dump(mode="json")
    assert set(document) == {
        "schema_version",
        "build_id",
        "fps",
        "max_duration_seconds",
        "width",
        "height",
        "duration_in_frames",
        "selected_capability_ids",
        "narration_cues",
        "audio_tracks",
        "assets",
        "sample_frames",
        "watermark",
        "seed",
    }
    assert document["narration_cues"] == [
        {"cue_id": "opening", "start_frame": 0, "duration_in_frames": 15},
        {"cue_id": "close", "start_frame": 15, "duration_in_frames": 31},
    ]
    assert document["audio_tracks"][1] == {
        "cue_id": "close",
        "src": "narration-close.wav",
        "start_frame": 15,
        "duration_in_frames": 31,
        "volume": 1.0,
    }
    assert document["assets"] == [
        {"id": "logo", "path": "assets/logo.svg", "kind": "svg"}
    ]
    assert document["sample_frames"][0] == {"frame": 0, "reason": "first"}
    assert document["sample_frames"][-1] == {"frame": 45, "reason": "final"}
    assert {sample["reason"] for sample in document["sample_frames"]} >= {
        "cue-start:close",
        "cue-end:opening",
    }
    assert document["selected_capability_ids"] == [
        "font.inter",
        "video.component.chart",
    ]


@pytest.mark.parametrize("duration_seconds", [180.0, 209.99, 210.0])
def test_scheduler_accepts_target_and_hard_headroom(duration_seconds: float) -> None:
    project = _project().model_copy(
        update={"narration_cues": (_project().narration_cues[0],)}
    )
    timeline = compile_video_timeline(
        project,
        [
            {
                "cue_id": "opening",
                "audio": "opening.wav",
                "duration_seconds": duration_seconds,
            }
        ],
    )

    assert timeline.duration_in_frames <= 6300


def test_scheduler_reports_cue_budgets_targeting_soft_limit() -> None:
    measured = _narration()
    measured[0]["duration_seconds"] = 110
    measured[1]["duration_seconds"] = 110

    with pytest.raises(VideoTimelineDurationError) as raised:
        compile_video_timeline(_project(), measured)

    error = raised.value
    assert (error.max_frames, error.compiled_frames, error.overflow_frames) == (
        6300,
        6600,
        300,
    )
    assert [
        (budget.cue_id, budget.max_seconds, budget.max_words)
        for budget in error.suggested_narration_budgets
    ] == [
        ("opening", 90.0, 225),
        ("close", 90.0, 225),
    ]


def test_scheduler_rejects_missing_duplicate_and_unsafe_measurements() -> None:
    with pytest.raises(ValueError, match="coverage mismatch"):
        compile_video_timeline(_project(), _narration()[:1])

    duplicate = [_narration()[0], _narration()[0]]
    with pytest.raises(ValueError, match="must be unique"):
        compile_video_timeline(_project(), duplicate)

    unsafe = _narration()
    unsafe[0]["audio"] = "../outside.wav"
    with pytest.raises(ValueError, match="confined"):
        compile_video_timeline(_project(), unsafe)


def test_runtime_contract_rejects_timing_drift_and_visual_structures() -> None:
    document = build_video_render_input(
        _project(),
        _narration(),
        build_id="build-12345678",
    ).model_dump()
    document["audio_tracks"][1]["start_frame"] = 16
    with pytest.raises(ValidationError, match="must match"):
        VideoRenderInput.model_validate(document)

    document = build_video_render_input(
        _project(),
        _narration(),
        build_id="build-12345678",
    ).model_dump()
    document["beats"] = []
    with pytest.raises(ValidationError, match="beats"):
        VideoRenderInput.model_validate(document)
