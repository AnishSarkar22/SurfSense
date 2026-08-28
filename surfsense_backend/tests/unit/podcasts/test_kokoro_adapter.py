from __future__ import annotations

import asyncio

import pytest

from app.podcasts.tts.adapters import kokoro
from app.podcasts.tts.errors import TextToSpeechError
from app.podcasts.tts.request import SynthesisRequest


class _RecordingProcess:
    def __init__(self, *, result: bytes = b"RIFF-test") -> None:
        self.requests: list[SynthesisRequest] = []
        self.result = result
        self.active = 0
        self.max_active = 0

    async def synthesize(self, request: SynthesisRequest) -> bytes:
        self.requests.append(request)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        return self.result


async def test_adapter_delegates_to_process_and_preserves_audio_contract(monkeypatch):
    process = _RecordingProcess()
    monkeypatch.setattr(kokoro, "KokoroProcess", lambda: process)
    request = SynthesisRequest("Hello", "af_heart", "en-US")

    audio = await kokoro.KokoroTextToSpeech().synthesize(request)

    assert process.requests == [request]
    assert audio.data == b"RIFF-test"
    assert audio.container == "wav"
    assert audio.sample_rate == 24_000


async def test_adapter_rejects_non_string_voice_before_starting_process(monkeypatch):
    process = _RecordingProcess()
    monkeypatch.setattr(kokoro, "KokoroProcess", lambda: process)
    adapter = kokoro.KokoroTextToSpeech()

    with pytest.raises(TextToSpeechError, match="named by string"):
        await adapter.synthesize(SynthesisRequest("Hello", {"name": "voice"}, "en-US"))

    assert process.requests == []


async def test_adapter_rejects_unknown_language_before_starting_process(monkeypatch):
    process = _RecordingProcess()
    monkeypatch.setattr(kokoro, "KokoroProcess", lambda: process)
    adapter = kokoro.KokoroTextToSpeech()

    with pytest.raises(TextToSpeechError, match="ko"):
        await adapter.synthesize(SynthesisRequest("Hello", "af_heart", "ko"))

    assert process.requests == []


def test_adapter_is_usable_across_fresh_event_loops(monkeypatch):
    process = _RecordingProcess()
    monkeypatch.setattr(kokoro, "KokoroProcess", lambda: process)
    adapter = kokoro.KokoroTextToSpeech()
    request = SynthesisRequest("Hello", "af_heart", "en-US")

    asyncio.run(adapter.synthesize(request))
    asyncio.run(adapter.synthesize(request))

    assert process.requests == [request, request]


async def test_process_errors_remain_public_tts_errors(monkeypatch):
    class FailingProcess:
        async def synthesize(self, _request: SynthesisRequest) -> bytes:
            raise TextToSpeechError("Kokoro synthesis failed: model failed")

    monkeypatch.setattr(kokoro, "KokoroProcess", FailingProcess)

    with pytest.raises(TextToSpeechError, match="Kokoro synthesis failed"):
        await kokoro.KokoroTextToSpeech().synthesize(
            SynthesisRequest("Hello", "af_heart", "en-US")
        )
