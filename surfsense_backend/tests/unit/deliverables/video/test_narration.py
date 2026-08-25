from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.deliverables.video import narration
from app.sandbox import ExecResult

pytestmark = pytest.mark.unit


class _Sandbox:
    session_id = "narration-test"

    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    async def write_file(self, path: str, data: bytes) -> None:
        self.writes[path] = data

    async def run_command(self, command: str) -> ExecResult:
        return ExecResult('{"format":{"duration":"0.25"}}', 0)


def _patch_dependencies(monkeypatch):
    captured: dict[str, object] = {}
    requests: list[str] = []

    @asynccontextmanager
    async def db_session():
        yield object()

    async def resolve_billing(_session, workspace_id, *, thread_id=None):
        assert workspace_id == 7
        assert thread_id == 41
        return uuid4(), "free", "test-model"

    @asynccontextmanager
    async def billing(**kwargs):
        captured.update(kwargs)
        yield

    async def synthesize(transcript, _voice, _language):
        requests.append(transcript)
        return b"audio"

    monkeypatch.setattr(narration, "shielded_async_session", db_session)
    monkeypatch.setattr(
        narration,
        "_resolve_agent_billing_for_workspace",
        resolve_billing,
    )
    monkeypatch.setattr(narration, "billable_call", billing)
    monkeypatch.setattr(narration, "_synthesize", synthesize)
    monkeypatch.setattr(
        narration,
        "_resolve_narration",
        lambda _language: SimpleNamespace(language="ja", voice="ja-voice"),
    )
    monkeypatch.setattr(
        narration,
        "get_text_to_speech",
        lambda: SimpleNamespace(container="wav"),
    )
    return captured, requests


async def test_synthesis_preserves_billing_concurrency_and_beat_identities(
    monkeypatch,
) -> None:
    billing, requests = _patch_dependencies(monkeypatch)
    sandbox = _Sandbox()

    result = await narration.synthesize_narration(
        [
            {
                "beat_id": "opening",
                "utterance_id": "opening-ja",
                "transcript": "  最初の説明。 ",
            },
            {
                "beat_id": "close",
                "utterance_id": "close-ja",
                "transcript": "次の説明。",
            },
        ],
        "/workspace/video-render-abc",
        workspace_id=7,
        thread_id=41,
        session=sandbox,
        language="ja",
    )

    assert result == [
        {
            "beat_id": "opening",
            "utterance_id": "opening-ja",
            "audio": "utterance-opening-ja.wav",
            "duration_seconds": 0.25,
        },
        {
            "beat_id": "close",
            "utterance_id": "close-ja",
            "audio": "utterance-close-ja.wav",
            "duration_seconds": 0.25,
        },
    ]
    assert requests == ["最初の説明。", "次の説明。"]
    assert set(sandbox.writes) == {
        "/workspace/video-render-abc/public/utterance-opening-ja.wav",
        "/workspace/video-render-abc/public/utterance-close-ja.wav",
    }
    assert billing["usage_type"] == "video_presentation_generation"
    assert billing["call_details"] == {
        "thread_id": 41,
        "beat_count": 2,
        "language": "ja",
        "tts_service": narration.app_config.TTS_SERVICE,
    }


@pytest.mark.parametrize(
    "workdir",
    [
        "workspace/render",
        "/workspace",
        "/tmp/render",
        "/workspace/render/../../tmp/escape",
    ],
)
async def test_path_confinement_prevents_paid_synthesis(
    monkeypatch,
    workdir,
) -> None:
    _patch_dependencies(monkeypatch)
    called = False

    async def synthesize(*_args):
        nonlocal called
        called = True
        return b"audio"

    monkeypatch.setattr(narration, "_synthesize", synthesize)
    with pytest.raises(ValueError, match="workdir"):
        await narration.synthesize_narration(
            [
                {
                    "beat_id": "opening",
                    "utterance_id": "opening",
                    "transcript": "Narration.",
                }
            ],
            workdir,
            workspace_id=7,
            thread_id=41,
            session=_Sandbox(),
        )
    assert called is False


async def test_oversized_measurement_is_returned_for_timeline_repair(
    monkeypatch,
) -> None:
    _patch_dependencies(monkeypatch)

    async def duration(_session, _path):
        return 180.000001

    monkeypatch.setattr(narration, "_probe_audio_duration", duration)
    result = await narration.synthesize_narration(
        [
            {
                "beat_id": "opening",
                "utterance_id": "opening",
                "transcript": "Narration.",
            }
        ],
        "/workspace/video-render-abc",
        workspace_id=7,
        thread_id=41,
        session=_Sandbox(),
    )

    assert result[0]["duration_seconds"] == 180.000001


async def test_max_words_is_rejected_before_billing_or_tts(monkeypatch) -> None:
    billing_called = False
    tts_called = False

    async def resolve_billing(*_args, **_kwargs):
        nonlocal billing_called
        billing_called = True

    async def synthesize(*_args):
        nonlocal tts_called
        tts_called = True
        return b"audio"

    monkeypatch.setattr(
        narration,
        "_resolve_agent_billing_for_workspace",
        resolve_billing,
    )
    monkeypatch.setattr(narration, "_synthesize", synthesize)

    with pytest.raises(ValueError, match="has 3 words; max_words is 2"):
        await narration.synthesize_narration(
            [
                {
                    "beat_id": "opening",
                    "utterance_id": "opening",
                    "transcript": "One two three.",
                    "max_words": 2,
                }
            ],
            "/workspace/video-render-abc",
            workspace_id=7,
            thread_id=41,
            session=_Sandbox(),
        )

    assert billing_called is False
    assert tts_called is False


def test_selective_audio_replacement_preserves_order_and_untouched_rows() -> None:
    opening = {
        "beat_id": "opening",
        "utterance_id": "opening",
        "audio": "opening.wav",
        "duration_seconds": 1.0,
    }
    middle = {
        "beat_id": "middle",
        "utterance_id": "middle",
        "audio": "middle.wav",
        "duration_seconds": 2.0,
    }
    close = {
        "beat_id": "close",
        "utterance_id": "close",
        "audio": "close.wav",
        "duration_seconds": 3.0,
    }
    replacement = {
        "beat_id": "middle",
        "utterance_id": "middle",
        "audio": "middle-repaired.wav",
        "duration_seconds": 1.5,
    }

    merged = narration.merge_narration_audio(
        [opening, middle, close],
        [replacement],
    )

    assert merged == [opening, replacement, close]
    assert merged[0] is opening
    assert merged[2] is close

    with pytest.raises(ValueError, match="not covered"):
        narration.merge_narration_audio(
            [opening, middle, close],
            [
                {
                    **replacement,
                    "beat_id": "unknown",
                }
            ],
        )
