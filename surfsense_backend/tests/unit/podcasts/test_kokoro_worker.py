from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.podcasts.tts.adapters import kokoro_worker
from app.podcasts.tts.errors import TextToSpeechError


def _request(output_path, *, text: str = "Hello") -> dict[str, object]:
    return {
        "text": text,
        "voice": "af_heart",
        "language": "en-US",
        "speed": 1.0,
        "output_path": str(output_path),
    }


def test_worker_reuses_pipeline_and_writes_valid_wav_atomically(tmp_path, monkeypatch):
    constructed = 0

    class FakePipeline:
        def __init__(self, *, lang_code: str) -> None:
            nonlocal constructed
            assert lang_code == "a"
            constructed += 1

        def __call__(self, *_args, **_kwargs):
            yield None, None, np.zeros(240, dtype=np.float32)

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=FakePipeline))
    worker = kokoro_worker._KokoroWorker()
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"

    worker.synthesize(_request(first))
    worker.synthesize(_request(second))

    assert constructed == 1
    assert first.read_bytes().startswith(b"RIFF")
    assert second.read_bytes().startswith(b"RIFF")
    assert not list(tmp_path.glob("*.partial"))


def test_worker_rejects_empty_audio_without_publishing_output(tmp_path, monkeypatch):
    class EmptyPipeline:
        def __init__(self, *, lang_code: str) -> None:
            assert lang_code == "a"

        def __call__(self, *_args, **_kwargs):
            return iter(())

    monkeypatch.setitem(sys.modules, "kokoro", SimpleNamespace(KPipeline=EmptyPipeline))
    output = tmp_path / "output.wav"

    with pytest.raises(TextToSpeechError, match="produced no audio"):
        kokoro_worker._KokoroWorker().synthesize(_request(output))

    assert not output.exists()
    assert not output.with_suffix(".wav.partial").exists()


def test_worker_rejects_unknown_or_extra_protocol_fields(tmp_path):
    request = _request(tmp_path / "output.wav")
    request["unexpected"] = True

    with pytest.raises(ValueError, match="invalid Kokoro process request"):
        kokoro_worker._KokoroWorker().synthesize(request)
