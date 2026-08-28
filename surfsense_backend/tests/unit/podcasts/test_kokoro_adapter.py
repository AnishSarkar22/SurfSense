from __future__ import annotations

import asyncio
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app.podcasts.tts.adapters import kokoro
from app.podcasts.tts.errors import TextToSpeechError
from app.podcasts.tts.request import SynthesisRequest


async def test_complete_synthesis_runs_off_the_event_loop_thread(monkeypatch):
    event_loop_thread = threading.get_ident()
    execution_threads: list[int] = []

    class FakePipeline:
        def __init__(self, *, lang_code: str) -> None:
            assert lang_code == "a"
            execution_threads.append(threading.get_ident())

        def __call__(self, *_args, **_kwargs):
            execution_threads.append(threading.get_ident())
            yield None, None, object()

    def fake_encode(_segments, sample_rate: int) -> bytes:
        assert sample_rate == 24000
        execution_threads.append(threading.get_ident())
        return b"RIFF-test"

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FakePipeline))
    monkeypatch.setattr(kokoro, "_encode_wav", fake_encode)

    audio = await kokoro.KokoroTextToSpeech().synthesize(
        SynthesisRequest(
            text="Hello",
            voice="af_heart",
            language="en-US",
        )
    )

    assert audio.data == b"RIFF-test"
    assert audio.container == "wav"
    assert audio.sample_rate == 24000
    assert len(set(execution_threads)) == 1
    assert execution_threads[0] != event_loop_thread


async def test_concurrent_syntheses_are_serialized(monkeypatch):
    active = 0
    max_active = 0
    lock = threading.Lock()

    class FakePipeline:
        def __init__(self, *, lang_code: str) -> None:
            assert lang_code == "a"

        def __call__(self, *_args, **_kwargs):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            yield None, None, object()
            with lock:
                active -= 1

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FakePipeline))
    monkeypatch.setattr(kokoro, "_encode_wav", lambda *_args: b"RIFF-test")
    adapter = kokoro.KokoroTextToSpeech()
    request = SynthesisRequest(
        text="Hello",
        voice="af_heart",
        language="en-US",
    )

    await asyncio.gather(adapter.synthesize(request), adapter.synthesize(request))

    assert max_active == 1


def test_adapter_reuses_a_pipeline_across_fresh_event_loops(monkeypatch):
    constructed = 0

    class FakePipeline:
        def __init__(self, *, lang_code: str) -> None:
            nonlocal constructed
            assert lang_code == "a"
            constructed += 1

        def __call__(self, *_args, **_kwargs):
            yield None, None, object()

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FakePipeline))
    monkeypatch.setattr(kokoro, "_encode_wav", lambda *_args: b"RIFF-test")
    adapter = kokoro.KokoroTextToSpeech()
    request = SynthesisRequest("Hello", "af_heart", "en-US")

    asyncio.run(adapter.synthesize(request))
    asyncio.run(adapter.synthesize(request))

    assert constructed == 1


async def test_synthesis_returns_a_valid_24_khz_wav(monkeypatch):
    class FakePipeline:
        def __init__(self, *, lang_code: str) -> None:
            assert lang_code == "a"

        def __call__(self, *_args, **_kwargs):
            yield None, None, np.zeros(240, dtype=np.float32)

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FakePipeline))

    audio = await kokoro.KokoroTextToSpeech().synthesize(
        SynthesisRequest("Hello", "af_heart", "en-US")
    )

    assert audio.data.startswith(b"RIFF")
    assert audio.sample_rate == 24000


async def test_empty_and_failed_generation_preserve_public_errors(monkeypatch):
    class EmptyPipeline:
        def __init__(self, *, lang_code: str) -> None:
            assert lang_code == "a"

        def __call__(self, *_args, **_kwargs):
            return iter(())

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=EmptyPipeline))
    request = SynthesisRequest("Hello", "af_heart", "en-US")

    with pytest.raises(TextToSpeechError, match="produced no audio"):
        await kokoro.KokoroTextToSpeech().synthesize(request)

    class FailingPipeline(EmptyPipeline):
        def __call__(self, *_args, **_kwargs):
            raise ValueError("model failed")

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FailingPipeline))
    with pytest.raises(TextToSpeechError, match="Kokoro synthesis failed: model failed"):
        await kokoro.KokoroTextToSpeech().synthesize(request)
