import asyncio
import json
import shlex
import shutil

import pytest

from app.artifacts.verification.formats.video import check_video
from app.sandbox import ExecResult

pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="ffmpeg and ffprobe are required",
)

BUILD_ID = "0123456789abcdefabcd"
RUNTIME_BUILD_ID = "fedcba9876543210abcd"


class LocalCommandSession:
    session_id = "local-ffmpeg"

    async def run_command(self, command):
        if command.startswith('index="${SURFSENSE_CAPABILITY_INDEX'):
            return ExecResult(
                json.dumps(
                    {
                        "schema_version": 1,
                        "build_id": BUILD_ID,
                        "runtime_build_id": RUNTIME_BUILD_ID,
                        "capabilities": [
                            {"id": "font.inter"},
                            {"id": "video.renderer.master"},
                        ],
                    }
                ),
                0,
            )
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await process.communicate()
        return ExecResult(output.decode(), process.returncode or 0)


async def _make_fixture(path, *, black=False, audio=True):
    video_source = (
        "color=c=black:s=1920x1080:r=30" if black else "testsrc2=s=1920x1080:r=30"
    )
    audio_input = "-f lavfi -i sine=frequency=440:sample_rate=48000" if audio else ""
    audio_codec = "-c:a aac -shortest" if audio else "-an"
    command = (
        f"ffmpeg -y -v error -f lavfi -i {shlex.quote(video_source)} "
        f"{audio_input} -t 1 -c:v libx264 -preset ultrafast -pix_fmt yuv420p "
        f"{audio_codec} {shlex.quote(str(path))}"
    )
    result = await LocalCommandSession().run_command(command)
    assert result.ok, result.output
    path.with_name(f"{path.name}.render.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "build_id": BUILD_ID,
                "capability_build_id": BUILD_ID,
                "runtime_build_id": RUNTIME_BUILD_ID,
                "input_sha256": "c" * 64,
                "source_sha256": "d" * 64,
                "bundle_sha256": "e" * 64,
                "expected_duration_seconds": 1,
                "expected_frame_count": 30,
                "sample_frames": [
                    {"frame": 0, "reason": "opening"},
                    {"frame": 15, "reason": "middle"},
                    {"frame": 29, "reason": "closing"},
                ],
                "selected_capability_ids": [
                    "font.inter",
                    "video.renderer.master",
                ],
                "resolved_capability_ids": [
                    "font.inter",
                    "video.renderer.master",
                ],
                "imported_capability_ids": [],
                "selected_capability_count": 2,
                "resolved_capability_count": 2,
                "render_settings": {
                    "codec": "h264",
                    "audio_codec": "aac",
                    "pixel_format": "yuv420p",
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                },
                "render_seconds": 0.5,
            }
        )
    )


async def test_real_ffmpeg_video_fixtures_cover_structural_gate(tmp_path):
    valid = tmp_path / "valid.mp4"
    black = tmp_path / "black.mp4"
    mute = tmp_path / "mute.mp4"
    await _make_fixture(valid)
    await _make_fixture(black, black=True)
    await _make_fixture(mute, audio=False)
    session = LocalCommandSession()

    assert (await check_video(session, str(valid))).structural.clean
    assert "single-color" in " ".join(
        (await check_video(session, str(black))).structural.findings
    )
    assert "narration audio" in " ".join(
        (await check_video(session, str(mute))).structural.findings
    )

    sidecar = tmp_path / "valid.mp4.render.json"
    metadata = json.loads(sidecar.read_text())
    metadata["expected_duration_seconds"] = 3
    sidecar.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="render metadata is invalid"):
        await check_video(session, str(valid))
