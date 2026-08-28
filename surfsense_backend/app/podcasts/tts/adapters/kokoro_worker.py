"""Isolated Kokoro inference process.

The parent adapter owns lifecycle and cancellation. This module owns the only
Kokoro pipeline cache and performs synchronous inference on the child process's
main thread.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import socket
from pathlib import Path
from typing import Any

from ..errors import TextToSpeechError

_SAMPLE_RATE = 24_000
_MAX_ERROR_CHARS = 2_000
_REQUEST_FIELDS = {"text", "voice", "language", "speed", "output_path"}
_LANG_CODE_BY_PRIMARY = {
    "en": "a",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "ja": "j",
    "pt": "p",
    "zh": "z",
}


def _lang_code(language: str) -> str:
    normalised = language.strip().lower()
    if normalised.startswith("en-gb") or normalised == "en-uk":
        return "b"
    primary = normalised.partition("-")[0]
    code = _LANG_CODE_BY_PRIMARY.get(primary)
    if code is None:
        raise TextToSpeechError(f"Kokoro has no language model for {language!r}")
    return code


def _encode_wav(segments: list[Any], sample_rate: int) -> bytes:
    import numpy as np
    import soundfile as sf

    waveform = segments[0] if len(segments) == 1 else np.concatenate(segments)
    buffer = io.BytesIO()
    sf.write(buffer, waveform, sample_rate, format="WAV")
    return buffer.getvalue()


class _KokoroWorker:
    def __init__(self) -> None:
        self._pipelines: dict[str, Any] = {}

    def synthesize(self, request: dict[str, object]) -> None:
        if set(request) != _REQUEST_FIELDS:
            raise ValueError("invalid Kokoro process request")

        text = request["text"]
        voice = request["voice"]
        language = request["language"]
        speed = request["speed"]
        output_path_value = request["output_path"]
        if not all(
            isinstance(value, str)
            for value in (text, voice, language, output_path_value)
        ) or not isinstance(speed, int | float):
            raise ValueError("invalid Kokoro process request")

        lang_code = _lang_code(language)
        pipeline = self._pipelines.get(lang_code)
        if pipeline is None:
            from kokoro import KPipeline

            pipeline = KPipeline(lang_code=lang_code)
            self._pipelines[lang_code] = pipeline

        segments = [
            audio
            for _gs, _ps, audio in pipeline(
                text,
                voice=voice,
                speed=float(speed),
                split_pattern=r"\n+",
            )
        ]
        if not segments:
            raise TextToSpeechError("Kokoro produced no audio for the text")

        audio = _encode_wav(segments, _SAMPLE_RATE)
        if not audio.startswith(b"RIFF"):
            raise TextToSpeechError("Kokoro produced invalid WAV audio")

        output_path = Path(output_path_value)
        partial_path = output_path.with_suffix(f"{output_path.suffix}.partial")
        try:
            partial_path.write_bytes(audio)
            os.replace(partial_path, output_path)
        finally:
            partial_path.unlink(missing_ok=True)


def _send(control: socket.socket, response: dict[str, object]) -> None:
    control.sendall(
        json.dumps(response, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"
    )


def _serve(control: socket.socket) -> None:
    worker = _KokoroWorker()
    buffer = bytearray()
    while True:
        chunk = control.recv(65_536)
        if not chunk:
            return
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, remainder = buffer.partition(b"\n")
            buffer = bytearray(remainder)
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("invalid Kokoro process request")
                worker.synthesize(request)
                _send(control, {"ok": True})
            except Exception as exc:
                _send(
                    control,
                    {
                        "ok": False,
                        "error": str(exc)[-_MAX_ERROR_CHARS:] or type(exc).__name__,
                    },
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-fd", type=int, required=True)
    args = parser.parse_args()
    with socket.socket(fileno=args.control_fd) as control:
        _serve(control)


if __name__ == "__main__":
    main()
