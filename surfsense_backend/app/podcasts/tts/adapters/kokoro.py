"""Local Kokoro adapter backed by one isolated, warm child process."""

from __future__ import annotations

from ..audio import SynthesizedAudio
from ..errors import TextToSpeechError
from ..port import TextToSpeech
from ..request import SynthesisRequest
from .kokoro_process import KokoroProcess
from .kokoro_worker import _lang_code

_SAMPLE_RATE = 24_000


class KokoroTextToSpeech(TextToSpeech):
    """Synthesise segments through the shared process-isolation boundary."""

    def __init__(self) -> None:
        self._process = KokoroProcess()

    @property
    def container(self) -> str:
        return "wav"

    async def synthesize(self, request: SynthesisRequest) -> SynthesizedAudio:
        if not isinstance(request.voice, str):
            raise TextToSpeechError("Kokoro voices are named by string, not a mapping")
        _lang_code(request.language)
        data = await self._process.synthesize(request)

        return SynthesizedAudio(
            data=data,
            container="wav",
            sample_rate=_SAMPLE_RATE,
        )
