import json

import pytest

from app.artifacts.verification.formats.registry import get_format_adapter
from app.artifacts.verification.formats.video import check_video
from app.sandbox import ExecResult


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
                    "duration": "3.0",
                    "nb_read_packets": str(self.probed_frames),
                }
            ]
            if self.audio:
                streams.append(
                    {
                        "codec_type": "audio",
                        "codec_name": self.audio_codec,
                        "duration": "3.0",
                        "nb_read_packets": "120",
                    }
                )
            return ExecResult(
                json.dumps({"format": {"duration": "3.0"}, "streams": streams}),
                0,
            )
        if command.startswith("test -f"):
            sidecar = self.sidecar or {
                "build_id": "0123456789abcdefabcd",
                "expected_duration_seconds": self.expected_duration,
                "expected_frame_count": self.expected_frames,
                "beat_sample_frames": [
                    {"frame": 0, "reason": "first-content"},
                    {"frame": 45, "reason": "beat:one:midpoint"},
                    {"frame": self.expected_frames - 1, "reason": "last-content"},
                ],
                "selected_capability_ids": [
                    "font.inter",
                    "video.component.core.primitives",
                    "video.renderer.master",
                ],
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
            }
            return ExecResult(json.dumps(sidecar), 0)
        if command.startswith('index="${SURFSENSE_CAPABILITY_INDEX'):
            return ExecResult(
                json.dumps(
                    {
                        "build_id": "0123456789abcdefabcd",
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
            return ExecResult(
                json.dumps(
                    [
                        {"levels": self.levels, "stddev": self.stddev}
                        for _ in range(3)
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
    sidecar = {
        "build_id": "build-1",
        "expected_duration_seconds": 3,
        "expected_frame_count": 90,
        "beat_sample_frames": [
            {"frame": 0, "reason": "first-content"},
            {"frame": 89, "reason": "last-content"},
        ],
        "selected_capability_ids": ["video.renderer.master"],
        "resolved_capability_ids": ["font.inter"],
        "selected_capability_count": 1,
        "resolved_capability_count": 1,
        "render_settings": {
            "codec": "h264",
            "audio_codec": "aac",
            "width": 1920,
            "height": 1080,
            "fps": 30,
        },
    }

    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(ProbeSession(sidecar=sidecar), "/workspace/out.mp4")


async def test_video_adapter_rejects_wrong_capability_build():
    sidecar = ProbeSession().sidecar
    session = ProbeSession()
    original_run_command = session.run_command

    async def wrong_build(command):
        if command.startswith('index="${SURFSENSE_CAPABILITY_INDEX'):
            return ExecResult(
                json.dumps({"build_id": "other-build", "capabilities": []}),
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
