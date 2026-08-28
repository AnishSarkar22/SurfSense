"""Fast, provider-independent checks for a rendered MP4."""

from __future__ import annotations

import json
import math
import re
import shlex
from typing import Any

from app.sandbox import SandboxSession

from .base import SandboxCheckResult, StructuralCheckResult

_WIDTH = 1920
_HEIGHT = 1080
_DURATION_TOLERANCE_SECONDS = 0.5
_MIN_FRAME_LEVELS = 4
_MIN_FRAME_STDDEV = 1.0
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BUILD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_CAPABILITY_ID_RE = re.compile(r"^(?:font|video\.(?:component|transition|renderer))\.")
_MAX_SAMPLE_FRAMES = 64
_SCHEMA_VERSION = 1
_RENDER_SETTINGS = {
    "codec": "h264",
    "audio_codec": "aac",
    "pixel_format": "yuv420p",
    "width": _WIDTH,
    "height": _HEIGHT,
    "fps": 30,
}
_RECEIPT_FIELDS = {
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


def reject_buffered_video_check(_: bytes) -> StructuralCheckResult:
    raise RuntimeError("Video verification must run inside the sandbox")


async def _run(session: SandboxSession, command: str, label: str) -> str:
    result = await session.run_command(command)
    if not result.ok:
        raise ValueError(f"Video {label} failed")
    return result.output.strip()


def _positive_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 and parsed == value else None


def _capability_ids(value: Any, *, allow_empty: bool = False) -> tuple[str, ...] | None:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(
            not isinstance(item, str) or not _CAPABILITY_ID_RE.match(item)
            for item in value
        )
        or value != sorted(value)
        or len(value) != len(set(value))
    ):
        return None
    return tuple(value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


async def _render_metadata(session: SandboxSession, path: str) -> dict[str, Any]:
    sidecar = f"{path}.render.json"
    result = await session.run_command(
        f"test -f {shlex.quote(sidecar)} && cat -- {shlex.quote(sidecar)}"
    )
    if not result.ok or not result.output.strip():
        raise ValueError("Video render metadata is missing")
    try:
        data = json.loads(result.output)
    except json.JSONDecodeError as exc:
        raise ValueError("Video render metadata is invalid") from exc
    if not isinstance(data, dict):
        raise ValueError("Video render metadata is invalid")

    expected_duration = _positive_float(data.get("expected_duration_seconds"))
    expected_frames = _positive_int(data.get("expected_frame_count"))
    render_seconds = _positive_float(data.get("render_seconds"))
    build_id = data.get("build_id")
    runtime_build_id = data.get("runtime_build_id")
    selected = _capability_ids(data.get("selected_capability_ids"))
    resolved = _capability_ids(data.get("resolved_capability_ids"))
    imported = _capability_ids(data.get("imported_capability_ids"), allow_empty=True)
    samples = data.get("sample_frames")
    settings = data.get("render_settings")
    if (
        set(data) != _RECEIPT_FIELDS
        or data.get("schema_version") != _SCHEMA_VERSION
        or expected_duration is None
        or expected_frames is None
        or render_seconds is None
        or expected_duration != expected_frames / _RENDER_SETTINGS["fps"]
        or not isinstance(build_id, str)
        or not _BUILD_ID_RE.fullmatch(build_id)
        or not isinstance(runtime_build_id, str)
        or not _BUILD_ID_RE.fullmatch(runtime_build_id)
        or not _is_sha256(data.get("input_sha256"))
        or not _is_sha256(data.get("source_sha256"))
        or not _is_sha256(data.get("bundle_sha256"))
        or data.get("capability_build_id") != build_id
        or selected is None
        or resolved is None
        or imported is None
        or not set(imported).issubset(selected)
        or data.get("selected_capability_count") != len(selected)
        or data.get("resolved_capability_count") != len(resolved)
        or not isinstance(samples, list)
        or not 1 <= len(samples) <= _MAX_SAMPLE_FRAMES
        or settings != _RENDER_SETTINGS
    ):
        raise ValueError("Video render metadata is invalid")

    frames: list[int] = []
    for sample in samples:
        if (
            not isinstance(sample, dict)
            or set(sample) != {"frame", "reason"}
            or not isinstance(sample.get("frame"), int)
            or isinstance(sample.get("frame"), bool)
            or not 0 <= sample["frame"] < expected_frames
            or not isinstance(sample.get("reason"), str)
            or not 1 <= len(sample["reason"]) <= 160
        ):
            raise ValueError("Video render metadata is invalid")
        frames.append(sample["frame"])
    if frames != sorted(frames) or len(frames) != len(set(frames)):
        raise ValueError("Video render metadata is invalid")

    index_result = await session.run_command(
        'index="${SURFSENSE_CAPABILITY_INDEX:-/opt/surfsense/capabilities/index.json}"; '
        'test -f "$index" && cat -- "$index"'
    )
    try:
        index = json.loads(index_result.output) if index_result.ok else None
        known_ids = {
            capability["id"]
            for capability in index["capabilities"]
            if isinstance(capability, dict) and isinstance(capability.get("id"), str)
        }
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Video capability index is invalid") from exc
    if (
        not isinstance(index, dict)
        or index.get("schema_version") != data["schema_version"]
        or index.get("build_id") != build_id
        or index.get("runtime_build_id") != runtime_build_id
        or not set(selected).issubset(known_ids)
        or not set(resolved).issubset(known_ids)
        or not set(imported).issubset(known_ids)
    ):
        raise ValueError("Video capability metadata does not match the sandbox build")
    expected_resolved = tuple(
        sorted(
            {
                "video.renderer.master",
                *imported,
                *(
                    capability_id
                    for capability_id in selected
                    if capability_id.startswith("font.")
                ),
            }
            & set(selected)
            & known_ids
        )
    )
    if resolved != expected_resolved:
        raise ValueError("Video capability metadata does not match the sandbox build")
    return data


async def check_video(session: SandboxSession, path: str) -> SandboxCheckResult:
    """Probe an MP4 in place; only compact metadata crosses the trust boundary."""
    quoted = shlex.quote(path)
    findings: list[str] = []
    metadata = await _render_metadata(session, path)
    probe_text = await _run(
        session,
        "ffprobe -v error -count_packets -of json -show_entries "
        "format=duration:stream=codec_type,codec_name,width,height,duration,"
        "nb_read_packets "
        f"{quoted}",
        "probe",
    )
    try:
        probe = json.loads(probe_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Video probe returned invalid metadata") from exc

    duration = _positive_float(probe.get("format", {}).get("duration"))
    if duration is None:
        findings.append("Video duration must be greater than zero")

    streams = probe.get("streams")
    if not isinstance(streams, list):
        streams = []
    video_streams = [
        stream for stream in streams if stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream for stream in streams if stream.get("codec_type") == "audio"
    ]
    if len(video_streams) != 1:
        findings.append("Video must contain exactly one video stream")
    else:
        video_stream = video_streams[0]
        if video_stream.get("codec_name") != "h264":
            findings.append("Video stream must use H.264")
        if video_stream.get("width") != _WIDTH or video_stream.get("height") != _HEIGHT:
            findings.append(f"Video resolution must be {_WIDTH}x{_HEIGHT}")
    if len(audio_streams) != 1:
        findings.append("Video must contain exactly one narration audio stream")
    else:
        audio_stream = audio_streams[0]
        if audio_stream.get("codec_name") != "aac":
            findings.append("Video narration audio must use AAC")
        try:
            audio_packets = int(audio_stream.get("nb_read_packets", 0))
        except (TypeError, ValueError):
            audio_packets = 0
        if audio_packets <= 0:
            findings.append("Video narration audio is empty")
        audio_duration = _positive_float(audio_stream.get("duration"))
        if (
            duration is not None
            and audio_duration is not None
            and duration - audio_duration > _DURATION_TOLERANCE_SECONDS
        ):
            findings.append("Video narration ends before the video")

    expected_duration = _positive_float(metadata["expected_duration_seconds"])
    if (
        duration is not None
        and expected_duration is not None
        and abs(duration - expected_duration) > _DURATION_TOLERANCE_SECONDS
    ):
        findings.append("Video duration does not match its render metadata")

    if len(video_streams) == 1:
        try:
            frame_count = int(video_streams[0].get("nb_read_packets", 0))
        except (TypeError, ValueError):
            frame_count = 0
        if frame_count != metadata["expected_frame_count"]:
            findings.append("Video frame count does not match its render metadata")

    sample_frames = [sample["frame"] for sample in metadata["sample_frames"]]
    if sample_frames:
        select = "+".join(f"eq(n\\,{frame})" for frame in sample_frames)
        frame_stats_text = await _run(
            session,
            "ffmpeg -v error "
            f"-i {quoted} -vf {shlex.quote(f'select={select},scale=64:36,format=gray')} "
            "-vsync 0 -f rawvideo - | "
            "python3 -c 'import json,statistics,sys; "
            "d=sys.stdin.buffer.read(); size=64*36; "
            "frames=[d[i:i+size] for i in range(0,len(d),size)]; "
            'print(json.dumps([{"levels":len(set(f)),'
            '"stddev":statistics.pstdev(f) if f else 0} for f in frames]))\'',
            "frame sanity checks",
        )
        try:
            frame_stats = json.loads(frame_stats_text)
            if not isinstance(frame_stats, list) or len(frame_stats) != len(
                sample_frames
            ):
                raise ValueError
            for frame, stats in zip(sample_frames, frame_stats, strict=True):
                if (
                    int(stats["levels"]) < _MIN_FRAME_LEVELS
                    or float(stats["stddev"]) < _MIN_FRAME_STDDEV
                ):
                    findings.append(
                        f"Video sampled frame {frame} is blank or single-color"
                    )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Video frame check returned invalid metadata") from exc

    primary_sha256 = (await _run(session, f"sha256sum -- {quoted}", "hash")).split(
        maxsplit=1
    )[0]
    if not _SHA256_RE.fullmatch(primary_sha256):
        raise ValueError("Video hash returned invalid metadata")

    return SandboxCheckResult(
        structural=StructuralCheckResult(tuple(findings)),
        primary_sha256=primary_sha256,
    )
