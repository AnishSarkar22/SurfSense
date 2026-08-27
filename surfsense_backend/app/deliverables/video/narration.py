"""Trusted synthesis and measurement for ordered narration cues."""

from __future__ import annotations

import asyncio
import json
import math
import re
import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TypedDict

from app.config import config as app_config
from app.db import shielded_async_session
from app.deliverables.jobs.policy import VIDEO_SPEC
from app.podcasts.resolution import DEFAULT_LANGUAGE, resolve_voices
from app.podcasts.schemas import normalize_language_tag
from app.podcasts.tts import SynthesisRequest, VoiceRef, get_text_to_speech
from app.podcasts.voices import (
    TtsProvider,
    VoiceCatalog,
    get_voice_catalog,
    provider_from_service,
)
from app.sandbox import SandboxSession
from app.services.billable_calls import (
    BillingSettlementError,
    QuotaInsufficientError,
    _resolve_agent_billing_for_workspace,
    billable_call,
)

_SANDBOX_WORKSPACE = PurePosixPath("/workspace")
_IDENTITY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_LEGACY_ENGLISH_VOICE_ID: dict[TtsProvider, str] = {
    TtsProvider.KOKORO: "kokoro:af_heart",
    TtsProvider.OPENAI: "openai:alloy",
    TtsProvider.AZURE: "azure:alloy",
    TtsProvider.VERTEX_AI: "vertex_ai:en-US-Studio-O",
}


class NarrationUtterance(TypedDict):
    cue_id: str
    transcript: str


class NarrationAudio(TypedDict):
    cue_id: str
    audio: str
    duration_seconds: float


def merge_narration_audio(
    original: list[NarrationAudio],
    replacements: list[NarrationAudio],
) -> list[NarrationAudio]:
    """Replace selected measured rows without changing timeline order."""

    original_by_id: dict[str, NarrationAudio] = {}
    for row in original:
        cue_id = row["cue_id"]
        if cue_id in original_by_id:
            raise ValueError("original narration cue IDs must be unique")
        original_by_id[cue_id] = row

    replacement_by_id: dict[str, NarrationAudio] = {}
    for row in replacements:
        cue_id = row["cue_id"]
        if cue_id in replacement_by_id:
            raise ValueError("replacement narration cue IDs must be unique")
        if cue_id not in original_by_id:
            raise ValueError(
                f"replacement narration cue is not covered by original: {cue_id}"
            )
        replacement_by_id[cue_id] = row

    return [replacement_by_id.get(row["cue_id"], row) for row in original]


@dataclass(frozen=True, slots=True)
class _NarrationVoice:
    language: str
    voice: VoiceRef


def _active_provider() -> TtsProvider:
    service = app_config.TTS_SERVICE
    if not service:
        raise ValueError("TTS_SERVICE is not configured")
    return provider_from_service(service)


def _supported_language(
    declared: str | None, *, provider: TtsProvider, catalog: VoiceCatalog
) -> str:
    for candidate in (declared, app_config.VIDEO_PRESENTATION_DEFAULT_LANGUAGE):
        if not candidate or not candidate.strip():
            continue
        try:
            language = normalize_language_tag(candidate)
        except ValueError:
            continue
        if catalog.supports_language(provider, language):
            return language
    return DEFAULT_LANGUAGE


def _resolve_narration(declared: str | None) -> _NarrationVoice:
    """Preserve the provider/language/voice policy used by queued video TTS."""

    provider = _active_provider()
    catalog = get_voice_catalog()
    language = _supported_language(declared, provider=provider, catalog=catalog)
    seed = _LEGACY_ENGLISH_VOICE_ID.get(provider)
    voice = resolve_voices(
        catalog=catalog,
        provider=provider,
        language=language,
        speaker_count=1,
        preferred=[seed] if seed else None,
    )[0].native_ref
    return _NarrationVoice(language=language, voice=voice)


async def _synthesize(transcript: str, voice: VoiceRef, language: str) -> bytes:
    audio = await get_text_to_speech().synthesize(
        SynthesisRequest(text=transcript, voice=voice, language=language)
    )
    if not audio.data:
        raise RuntimeError("TTS provider returned empty audio")
    return audio.data


def _public_audio_path(workdir: str, cue_id: str, extension: str) -> str:
    candidate = PurePosixPath(workdir)
    if (
        not candidate.is_absolute()
        or ".." in candidate.parts
        or candidate == _SANDBOX_WORKSPACE
        or not candidate.is_relative_to(_SANDBOX_WORKSPACE)
    ):
        raise ValueError(
            "workdir must be an absolute directory below /workspace without '..'"
        )
    if _IDENTITY.fullmatch(cue_id) is None:
        raise ValueError("cue_id must be a safe stable identity")
    if not extension or not extension.isalnum():
        raise ValueError("TTS provider returned an invalid audio container")
    return str(
        candidate / "public" / f"narration-{cue_id}.{extension.casefold()}"
    )


async def _write_into_public(
    session: SandboxSession,
    path: str,
    audio_bytes: bytes,
) -> str:
    await session.write_file(path, audio_bytes)
    return PurePosixPath(path).name


async def _probe_audio_duration(session: SandboxSession, path: str) -> float:
    result = await session.run_command(
        "ffprobe -v error -show_entries format=duration -of json -- "
        + shlex.quote(path)
    )
    if not result.ok:
        raise ValueError("Could not determine synthesized narration duration")
    try:
        duration = float(json.loads(result.output)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Synthesized narration returned invalid duration") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Synthesized narration duration must be positive")
    return duration


def _validated_utterances(
    utterances: list[NarrationUtterance],
) -> list[tuple[str, str, str]]:
    if not utterances:
        raise ValueError("utterances must contain at least one narration transcript")
    if len(utterances) > VIDEO_SPEC.max_narration_cues:
        raise ValueError(
            "utterances exceeds the "
            f"{VIDEO_SPEC.max_narration_cues}-cue video limit"
        )

    validated: list[tuple[str, str]] = []
    cue_ids: set[str] = set()
    for utterance in utterances:
        cue_id = utterance["cue_id"]
        transcript = utterance["transcript"]
        if not isinstance(cue_id, str) or _IDENTITY.fullmatch(cue_id) is None:
            raise ValueError("cue_id must be a safe stable identity")
        if cue_id in cue_ids:
            raise ValueError(f"duplicate cue_id: {cue_id}")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError(f"cue {cue_id!r} transcript must not be empty")
        cue_ids.add(cue_id)
        validated.append((cue_id, transcript.strip()))
    return validated


async def synthesize_narration(
    utterances: list[NarrationUtterance],
    workdir: str,
    *,
    workspace_id: int,
    thread_id: int,
    session: SandboxSession,
    language: str | None = None,
) -> list[NarrationAudio]:
    """Synthesize concurrently, bill once, persist, and measure each utterance."""

    validated = _validated_utterances(utterances)
    narration = _resolve_narration(language)
    extension = get_text_to_speech().container
    paths = [
        _public_audio_path(workdir, cue_id, extension)
        for cue_id, _ in validated
    ]

    async with shielded_async_session() as billing_session:
        owner_id, billing_tier, base_model = await _resolve_agent_billing_for_workspace(
            billing_session,
            workspace_id,
            thread_id=thread_id,
        )

    try:
        async with billable_call(
            user_id=owner_id,
            workspace_id=workspace_id,
            billing_tier=billing_tier,
            base_model=base_model,
            quota_reserve_micros_override=(
                app_config.QUOTA_DEFAULT_VIDEO_PRESENTATION_RESERVE_MICROS
            ),
            usage_type="video_presentation_generation",
            call_details={
                "thread_id": thread_id,
                "cue_count": len(validated),
                "language": narration.language,
                "tts_service": app_config.TTS_SERVICE,
            },
        ):
            audio_by_utterance = await asyncio.gather(
                *(
                    _synthesize(transcript, narration.voice, narration.language)
                    for _, transcript in validated
                )
            )
    except QuotaInsufficientError:
        raise RuntimeError("Out of credits for premium video generation.") from None
    except BillingSettlementError:
        raise RuntimeError("Video generation billing settlement failed.") from None

    filenames = await asyncio.gather(
        *(
            _write_into_public(session, path, audio_bytes)
            for path, audio_bytes in zip(paths, audio_by_utterance, strict=True)
        )
    )
    durations = await asyncio.gather(
        *(_probe_audio_duration(session, path) for path in paths)
    )
    return [
        {
            "cue_id": cue_id,
            "audio": filename,
            "duration_seconds": duration,
        }
        for (cue_id, _), filename, duration in zip(
            validated, filenames, durations, strict=True
        )
    ]
