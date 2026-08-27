import json

import pytest

from app.artifacts.verification.formats.registry import get_format_adapter
from app.artifacts.verification.formats.video import check_video
from app.sandbox import ExecResult

BUILD_ID = "0123456789abcdefabcd"
RUNTIME_BUILD_ID = "fedcba9876543210abcd"


def _receipt(*, expected_duration=3.0, expected_frames=90):
    return {
        "schema_version": 1,
        "build_id": BUILD_ID,
        "capability_build_id": BUILD_ID,
        "runtime_build_id": RUNTIME_BUILD_ID,
        "input_sha256": "c" * 64,
        "source_sha256": "d" * 64,
        "bundle_sha256": "e" * 64,
        "expected_duration_seconds": expected_duration,
        "expected_frame_count": expected_frames,
        "sample_frames": [
            {"frame": 0, "reason": "opening"},
            {"frame": 45, "reason": "middle"},
            {"frame": expected_frames - 1, "reason": "closing"},
        ],
        "selected_capability_ids": [
            "font.inter",
            "video.component.core.primitives",
            "video.renderer.master",
        ],
        "imported_capability_ids": ["video.component.core.primitives"],
        "resolved_capability_ids": [
            "font.inter",
            "video.component.core.primitives",
            "video.renderer.master",
        ],
        "selected_capability_count": 3,
        "resolved_capability_count": 3,
        "render_settings": {
            "codec": "h264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "width": 1920,
            "height": 1080,
            "fps": 30,
        },
        "render_seconds": 2.5,
    }


class ProbeSession:
    session_id = "sandbox-1"

    def __init__(
        self,
        *,
        audio=True,
        audio_codec="aac",
        video_codec="h264",
        levels=40,
        stddev=20.0,
        expected_duration=3.0,
        expected_frames=90,
        probed_duration=3.0,
        probed_frames=90,
        sidecar=None,
        sha256="a" * 64,
    ):
        self.audio = audio
        self.audio_codec = audio_codec
        self.video_codec = video_codec
        self.levels = levels
        self.stddev = stddev
        self.expected_duration = expected_duration
        self.expected_frames = expected_frames
        self.probed_duration = probed_duration
        self.probed_frames = probed_frames
        self.sidecar = sidecar
        self.sha256 = sha256
        self.commands = []

    async def run_command(self, command):
        self.commands.append(command)
        if command.startswith("ffprobe"):
            streams = [
                {
                    "codec_type": "video",
                    "codec_name": self.video_codec,
                    "width": 1920,
                    "height": 1080,
                    "duration": str(self.probed_duration),
                    "nb_read_packets": str(self.probed_frames),
                }
            ]
            if self.audio:
                streams.append(
                    {
                        "codec_type": "audio",
                        "codec_name": self.audio_codec,
                        "duration": str(self.probed_duration),
                        "nb_read_packets": "120",
                    }
                )
            return ExecResult(
                json.dumps(
                    {
                        "format": {"duration": str(self.probed_duration)},
                        "streams": streams,
                    }
                ),
                0,
            )
        if command.startswith("test -f"):
            sidecar = (
                self.sidecar
                if self.sidecar is not None
                else _receipt(
                    expected_duration=self.expected_duration,
                    expected_frames=self.expected_frames,
                )
            )
            return ExecResult(json.dumps(sidecar), 0)
        if command.startswith('index="${SURFSENSE_CAPABILITY_INDEX'):
            return ExecResult(
                json.dumps(
                    {
                        "schema_version": 1,
                        "build_id": BUILD_ID,
                        "runtime_build_id": RUNTIME_BUILD_ID,
                        "capabilities": [
                            {"id": "font.inter"},
                            {"id": "video.component.core.primitives"},
                            {"id": "video.renderer.master"},
                        ],
                    }
                ),
                0,
            )
        if command.startswith("ffmpeg"):
            sample_count = (
                len(self.sidecar["sample_frames"])
                if self.sidecar is not None and "sample_frames" in self.sidecar
                else 3
            )
            return ExecResult(
                json.dumps(
                    [
                        {"levels": self.levels, "stddev": self.stddev}
                        for _ in range(sample_count)
                    ]
                ),
                0,
            )
        if command.startswith("sha256sum"):
            return ExecResult(f"{self.sha256}  /workspace/out.mp4", 0)
        raise AssertionError(command)


async def test_video_adapter_probes_in_sandbox_and_requires_audio():
    adapter = get_format_adapter("/workspace/out.mp4")
    assert adapter.name == "video"
    assert adapter.requires_visual_review is False
    assert adapter.sandbox_check is check_video

    result = await check_video(ProbeSession(audio=False), "/workspace/out.mp4")

    assert result.primary_sha256 == "a" * 64
    assert result.structural.findings == (
        "Video must contain exactly one narration audio stream",
    )


async def test_video_adapter_rejects_single_color_frame():
    result = await check_video(ProbeSession(levels=1, stddev=0), "/workspace/out.mp4")

    assert "single-color" in result.structural.findings[0]


async def test_video_adapter_accepts_narrated_nonblank_mp4():
    session = ProbeSession()
    result = await check_video(session, "/workspace/out.mp4")

    assert result.structural.clean
    assert ".render.json" in session.commands[0]
    assert all(".segments.json" not in command for command in session.commands)
    frame_command = next(
        command for command in session.commands if command.startswith("ffmpeg")
    )
    assert all(f"eq(n\\,{frame})" in frame_command for frame in (0, 45, 89))
    assert set(_receipt()) == {
        "schema_version",
        "build_id",
        "capability_build_id",
        "runtime_build_id",
        "input_sha256",
        "source_sha256",
        "bundle_sha256",
        "expected_duration_seconds",
        "expected_frame_count",
        "sample_frames",
        "selected_capability_ids",
        "imported_capability_ids",
        "resolved_capability_ids",
        "selected_capability_count",
        "resolved_capability_count",
        "render_settings",
        "render_seconds",
    }


async def test_video_adapter_rejects_duration_and_frame_count_mismatch():
    result = await check_video(
        ProbeSession(expected_duration=5, expected_frames=150, probed_frames=90),
        "/workspace/out.mp4",
    )

    assert result.structural.findings == (
        "Video duration does not match its render metadata",
        "Video frame count does not match its render metadata",
    )


async def test_video_adapter_requires_h264_and_aac():
    result = await check_video(
        ProbeSession(video_codec="hevc", audio_codec="mp3"),
        "/workspace/out.mp4",
    )

    assert result.structural.findings == (
        "Video stream must use H.264",
        "Video narration audio must use AAC",
    )


async def test_video_adapter_rejects_inconsistent_capability_receipt():
    sidecar = _receipt()
    sidecar["resolved_capability_ids"] = ["font.inter"]
    sidecar["resolved_capability_count"] = 1

    with pytest.raises(ValueError, match="does not match the sandbox build"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


async def test_video_adapter_rejects_wrong_capability_build():
    sidecar = _receipt()
    session = ProbeSession()
    original_run_command = session.run_command

    async def wrong_build(command):
        if command.startswith('index="${SURFSENSE_CAPABILITY_INDEX'):
            return ExecResult(
                json.dumps(
                    {
                        "schema_version": 1,
                        "build_id": "other-build",
                        "runtime_build_id": RUNTIME_BUILD_ID,
                        "capabilities": [],
                    }
                ),
                0,
            )
        return await original_run_command(command)

    session.run_command = wrong_build
    session.sidecar = sidecar
    with pytest.raises(ValueError, match="does not match the sandbox build"):
        await check_video(session, "/workspace/out.mp4")


async def test_video_adapter_returns_exact_validated_sha256():
    expected = "0123456789abcdef" * 4
    result = await check_video(ProbeSession(sha256=expected), "/workspace/out.mp4")
    assert result.primary_sha256 == expected

    with pytest.raises(ValueError, match="hash returned invalid metadata"):
        await check_video(ProbeSession(sha256=expected.upper()), "/workspace/out.mp4")


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "build_id",
        "input_sha256",
        "source_sha256",
        "bundle_sha256",
        "runtime_build_id",
        "capability_build_id",
        "imported_capability_ids",
        "expected_frame_count",
        "expected_duration_seconds",
        "sample_frames",
        "render_settings",
        "render_seconds",
    ],
)
async def test_video_adapter_rejects_incomplete_current_receipt(field):
    sidecar = _receipt()
    del sidecar[field]

    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


async def test_video_adapter_rejects_unknown_receipt_fields():
    sidecar = _receipt()
    sidecar["unknown"] = True

    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


@pytest.mark.parametrize(
    ("field", "tampered"),
    [
        ("input_sha256", "0" * 63),
        ("source_sha256", "0" * 63),
        ("bundle_sha256", 123),
    ],
)
async def test_video_adapter_rejects_tampered_receipt_hash(field, tampered):
    sidecar = _receipt()
    sidecar[field] = tampered

    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


async def test_video_adapter_rejects_receipt_duration_not_derived_from_frames():
    sidecar = _receipt()
    sidecar["expected_duration_seconds"] = 4

    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


async def test_video_adapter_accepts_single_deduplicated_neutral_sample():
    sidecar = _receipt(expected_duration=1 / 30, expected_frames=1)
    sidecar["sample_frames"] = [{"frame": 0, "reason": "only-frame"}]

    result = await check_video(
        ProbeSession(
            expected_duration=1 / 30,
            expected_frames=1,
            probed_duration=1 / 30,
            probed_frames=1,
            sidecar=sidecar,
        ),
        "/workspace/out.mp4",
    )

    assert result.structural.clean


async def test_video_adapter_rejects_empty_narration_audio():
    session = ProbeSession()
    original_run_command = session.run_command

    async def empty_audio(command):
        result = await original_run_command(command)
        if command.startswith("ffprobe"):
            probe = json.loads(result.output)
            probe["streams"][1]["nb_read_packets"] = "0"
            return ExecResult(json.dumps(probe), 0)
        return result

    session.run_command = empty_audio
    result = await check_video(session, "/workspace/out.mp4")

    assert result.structural.findings == ("Video narration audio is empty",)


async def test_video_adapter_rejects_missing_video_asset():
    session = ProbeSession()
    original_run_command = session.run_command

    async def missing_video(command):
        if command.startswith("ffprobe"):
            return ExecResult("No such file", 1)
        return await original_run_command(command)

    session.run_command = missing_video
    with pytest.raises(ValueError, match="Video probe failed"):
        await check_video(session, "/workspace/missing.mp4")
