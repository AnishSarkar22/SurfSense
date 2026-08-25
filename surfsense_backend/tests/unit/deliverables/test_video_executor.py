from __future__ import annotations

import json
from pathlib import PurePosixPath
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.artifacts.service import ArtifactSaved
from app.deliverables.video import executor
from app.deliverables.video.compiler import compile_video_plan
from app.deliverables.video.contracts import (
    AuthoredCapabilityLayer,
    AuthoredTextLayer,
    AuthoredVideoBeat,
    AuthoredVideoPlan,
    AuthoredVideoStyle,
    Bounds,
    CreativeOutline,
    NarrationRewrite,
    NarrationRewriteBeat,
    VisualIntent,
)
from app.deliverables.video.skill import LoadedVideoSkill
from app.deliverables.video.timeline import (
    NarrationBudget,
    VideoTimelineDurationError,
    build_video_render_input,
)
from app.sandbox import SandboxResourceProfile
from app.sandbox.capabilities.schema import (
    CapabilityEnvelope,
    CapabilityIndex,
    CapabilityKind,
    CapabilityTier,
)
from tests.utils.fake_sandbox import FakeSandboxSession


def _job(**overrides):
    values = {
        "id": 7,
        "kind": "video",
        "title": "Quarterly update",
        "workspace_id": 3,
        "thread_id": 11,
        "tool_call_id": "tool-1",
        "celery_task_id": "deliverable-job:7:attempt:1",
        "attempt_count": 1,
        "request": {
            "version": 1,
            "brief": "Explain the quarter",
            "source_references": ["/documents/report.pdf"],
            "revision_artifact_id": None,
            "root_thread_id": 11,
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _capability(capability_id: str, kind: CapabilityKind) -> CapabilityEnvelope:
    return CapabilityEnvelope(
        id=capability_id,
        kind=kind,
        domain="video",
        category="core",
        summary=capability_id,
        tags=("core",),
        tier=CapabilityTier.CORE,
        declaration={},
        search_text=f"{capability_id} core",
    )


def _index() -> CapabilityIndex:
    return CapabilityIndex(
        schema_version=1,
        build_id="build-12345678",
        capabilities=(
            _capability("video.renderer.master", CapabilityKind.RENDERER),
            _capability("video.component.core.primitives", CapabilityKind.COMPONENT),
            _capability("font.inter", CapabilityKind.FONT),
            _capability("font.lora", CapabilityKind.FONT),
            _capability("font.jetbrains-mono", CapabilityKind.FONT),
        ),
    )


def _outline() -> CreativeOutline:
    return CreativeOutline(
        title="Quarterly update",
        objective="Explain growth",
        audience="Leadership",
        language="en",
        visual_intents=(
            VisualIntent(
                beat_id="opening",
                description="A clear quarterly growth headline",
            ),
        ),
    )


def _authored(
    *,
    narration: str = "Revenue grew in every region.",
    wrong_kind_slot: bool = False,
) -> AuthoredVideoPlan:
    layer = (
        AuthoredCapabilityLayer(
            type="capability",
            id="headline",
            bounds=Bounds(x=100, y=100, width=1200, height=400),
            capability_slot="capability-03",
        )
        if wrong_kind_slot
        else AuthoredTextLayer(
            type="text",
            id="headline",
            bounds=Bounds(x=100, y=100, width=1200, height=400),
            text="Quarterly growth",
            font_id="font.inter",
            font_size=96,
            color="#f8fafc",
        )
    )
    return AuthoredVideoPlan(
        title="Quarterly update",
        language="en",
        style=AuthoredVideoStyle(
            primary_font_id="font.inter",
            palette=("#020617", "#f8fafc"),
        ),
        beats=(
            AuthoredVideoBeat(
                beat_id="opening",
                utterance_id="opening-narration",
                narration=narration,
                layers=(layer,),
            ),
        ),
    )


def _skill() -> LoadedVideoSkill:
    return LoadedVideoSkill(
        content="Author a declarative VideoPlan.",
        sha256="a" * 64,
        files=("SKILL.md",),
    )


def test_video_request_and_model_contracts_are_strict_without_tsx() -> None:
    request = executor.VideoJobRequestV1.model_validate(_job().request)
    assert request.root_thread_id == 11
    with pytest.raises(ValidationError):
        executor.VideoJobRequestV1.model_validate({**_job().request, "version": 2})
    with pytest.raises(ValidationError):
        executor.VideoJobRequestV1.model_validate(
            {**_job().request, "revision_artifact_id": True}
        )

    schema = json.dumps(AuthoredVideoPlan.model_json_schema()).casefold()
    assert "tsx" not in schema
    assert "scene" not in schema
    assert "slide" not in schema
    assert not hasattr(executor, "AuthoredVideoScene")


def test_planning_disclosure_uses_slots_and_only_exposes_font_ids() -> None:
    disclosure = executor._retrieve_disclosure(_index(), _outline())
    payload = executor._authored_capability_disclosure(disclosure)

    assert payload["font_ids"] == [
        "font.inter",
        "font.lora",
        "font.jetbrains-mono",
    ]
    slots = payload["capability_slots"]
    assert [slot["slot"] for slot in slots] == [
        f"capability-{position:02d}" for position in range(1, 6)
    ]
    assert slots[1] == {
        "slot": "capability-02",
        "kind": "component",
        "metadata": {
            "category": "core",
            "summary": "video.component.core.primitives",
            "tags": ["core"],
            "vibe": [],
            "use_for": [],
            "avoid_for": [],
            "natural_frame_length": None,
        },
        "props_schema": None,
    }
    assert "id" not in slots[1]


async def test_visual_repair_preserves_narration_identity_and_language(
    monkeypatch,
) -> None:
    disclosure = executor._retrieve_disclosure(_index(), _outline())
    plan = compile_video_plan(_authored(), index=_index(), disclosure=disclosure)
    changed = _authored(narration="This narration was changed.")
    monkeypatch.setattr(executor, "_invoke_structured", AsyncMock(return_value=changed))

    with pytest.raises(ValueError, match="protected narration"):
        await executor._repair_plan(
            object(),
            skill=_skill(),
            plan=plan,
            findings="Headline clips",
            index=_index(),
            disclosure=disclosure,
        )


async def test_executor_repairs_wrong_kind_before_tts_and_orders_phases(
    monkeypatch,
) -> None:
    events: list[str] = []
    sandbox = FakeSandboxSession()
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    class Registry:
        async def get_session(self, owner, workspace_id, *, profile):
            assert (owner, workspace_id) == ("deliverable-job-7-attempt-1", 3)
            assert profile is SandboxResourceProfile.VIDEO_RENDER
            return sandbox

    async def heartbeat(*_args, phase, **_kwargs):
        events.append(phase)
        return SimpleNamespace(id=7)

    responses = iter(
        (
            _outline(),
            _authored(wrong_kind_slot=True),
            _authored(),
            NarrationRewrite(
                beats=(
                    NarrationRewriteBeat(
                        beat_id="opening",
                        utterance_id="opening-narration",
                        narration="Growth continued.",
                    ),
                )
            ),
        )
    )
    tts_calls = 0
    model_calls = 0

    async def model_call(*_args, **_kwargs):
        nonlocal model_calls
        model_calls += 1
        phase = _kwargs["payload"]["phase"]
        events.append(phase)
        if phase in {"video_plan", "semantic_compile_repair"}:
            assert _kwargs["model"] is AuthoredVideoPlan
        elif phase == "narration_duration_repair":
            assert _kwargs["model"] is NarrationRewrite
        return next(responses)

    async def narration(*_args, **_kwargs):
        nonlocal tts_calls
        tts_calls += 1
        events.append("tts")
        return [
            {
                "beat_id": "opening",
                "utterance_id": "opening-narration",
                "audio": "utterance-opening-narration.wav",
                "duration_seconds": 181.0 if tts_calls == 1 else 2.0,
            }
        ]

    issues = iter(("headline clipped", None))

    async def preflight(*_args, **_kwargs):
        events.append("preflight")
        return next(issues)

    async def repair(_llm, **kwargs):
        events.append("visual-repair")
        return kwargs["plan"]

    async def render(*_args):
        events.append("full-render")

    async def verify(*_args, **_kwargs):
        events.append("artifact-verify")
        return SimpleNamespace(verified=True, findings=())

    async def save(*_args, **_kwargs):
        events.append("save-artifact")
        return ArtifactSaved(
            status="saved",
            artifact_id=19,
            generation=1,
            title="Quarterly update",
            files=[],
        )

    monkeypatch.setattr(executor.app_config, "VIDEO_SANDBOX_RENDERING_ENABLED", True)
    monkeypatch.setattr(executor, "get_registry", AsyncMock(return_value=Registry()))
    monkeypatch.setattr(executor, "heartbeat_deliverable_job", heartbeat)
    monkeypatch.setattr(executor, "_stage_runtime", AsyncMock())
    monkeypatch.setattr(executor, "load_video_skill", AsyncMock(return_value=_skill()))
    monkeypatch.setattr(
        executor, "load_capability_index", AsyncMock(return_value=_index())
    )
    monkeypatch.setattr(executor, "_invoke_structured", model_call)
    monkeypatch.setattr(executor, "synthesize_narration", narration)
    monkeypatch.setattr(executor, "get_vision_llm", AsyncMock(return_value=None))
    monkeypatch.setattr(executor, "_preflight_and_review", preflight)
    monkeypatch.setattr(executor, "_repair_plan", repair)
    monkeypatch.setattr(executor, "_render", render)
    monkeypatch.setattr(executor, "verify_artifact", verify)
    monkeypatch.setattr(executor, "_save_verified", save)

    result = await executor.execute_video_deliverable(session, _job(), object())

    assert events == [
        "preparing",
        "outlining",
        "creative_outline",
        "retrieving",
        "planning",
        "video_plan",
        "semantic_compile_repair",
        "narrating",
        "tts",
        "repairing_narration",
        "narration_duration_repair",
        "tts",
        "reviewing",
        "preflight",
        "repairing",
        "visual-repair",
        "reviewing",
        "preflight",
        "rendering",
        "full-render",
        "verifying",
        "artifact-verify",
        "saving",
        "save-artifact",
    ]
    assert result.duration_seconds == 3
    assert result.beat_count == 1
    assert result.repair_count == 1
    assert tts_calls == 2
    assert model_calls == 4
    assert events.index("semantic_compile_repair") < events.index("tts")
    assert events.index("narration_duration_repair") < events.index("preflight")


async def test_narration_repair_is_bounded_to_text_and_preserves_identity(
    monkeypatch,
) -> None:
    disclosure = executor._retrieve_disclosure(_index(), _outline())
    plan = compile_video_plan(_authored(), index=_index(), disclosure=disclosure)
    rewrite = NarrationRewrite(
        beats=(
            NarrationRewriteBeat(
                beat_id="opening",
                utterance_id="opening-narration",
                narration="Growth continued.",
            ),
        )
    )
    invoke = AsyncMock(return_value=rewrite)
    monkeypatch.setattr(executor, "_invoke_structured", invoke)

    repaired, requests = await executor._request_narration_repair(
        object(),
        skill=_skill(),
        plan=plan,
        duration_error=VideoTimelineDurationError(
            compiled_frames=6000,
            suggested_narration_budgets=(
                NarrationBudget(
                    beat_id="opening",
                    max_seconds=2,
                    max_words=3,
                ),
            ),
        ),
    )

    assert repaired.beats[0].narration == "Growth continued."
    assert repaired.beats[0].layers == plan.beats[0].layers
    assert repaired.beats[0].utterance_id == plan.beats[0].utterance_id
    assert requests == [
        {
            "beat_id": "opening",
            "utterance_id": "opening-narration",
            "transcript": "Growth continued.",
            "max_words": 3,
        }
    ]
    assert invoke.await_args.kwargs["model"] is NarrationRewrite


async def test_publish_job_assets_targets_bundle_public() -> None:
    sandbox = FakeSandboxSession()

    await executor._publish_job_assets(
        sandbox, PurePosixPath("/workspace/deliverable-job-7-attempt-1")
    )

    assert sandbox.commands == [
        "cp -a --reflink=auto "
        "/workspace/deliverable-job-7-attempt-1/public/. "
        "/workspace/deliverable-job-7-attempt-1/bundle/public/"
    ]


def test_render_commands_use_the_isolated_job_bundle(monkeypatch) -> None:
    workdir = PurePosixPath("/workspace/deliverable-job-7-attempt-1")

    monkeypatch.setattr(executor.app_config, "VIDEO_SANDBOX_FRAME_CONCURRENCY", 2)
    assert executor._render_command(
        workdir,
        "--preflight",
        workdir / "props.json",
    ) == (
        "cd -- /workspace/deliverable-job-7-attempt-1 && "
        "VIDEO_SANDBOX_FRAME_CONCURRENCY=2 node render.mjs "
        "--bundle-dir /workspace/deliverable-job-7-attempt-1/bundle "
        "--preflight /workspace/deliverable-job-7-attempt-1/props.json"
    )


async def test_disabled_executor_stops_before_sandbox_or_model_work(
    monkeypatch,
) -> None:
    registry = AsyncMock()
    model = AsyncMock()
    monkeypatch.setattr(executor.app_config, "VIDEO_SANDBOX_RENDERING_ENABLED", False)
    monkeypatch.setattr(executor, "get_registry", registry)

    with pytest.raises(RuntimeError, match="disabled"):
        await executor.execute_video_deliverable(SimpleNamespace(), _job(), model)

    registry.assert_not_awaited()
    model.assert_not_awaited()


async def test_heartbeat_stops_work_when_cancellation_wins(monkeypatch) -> None:
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    monkeypatch.setattr(
        executor,
        "heartbeat_deliverable_job",
        AsyncMock(return_value=None),
    )

    with pytest.raises(executor.DeliverableJobCancellationError):
        await executor._heartbeat(session, 7, "rendering", 80)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_revision_save_uses_generation_and_exact_sha(monkeypatch) -> None:
    index = _index()
    disclosure = executor._retrieve_disclosure(index, _outline())
    plan = compile_video_plan(_authored(), index=index, disclosure=disclosure)
    render_input = build_video_render_input(
        plan,
        [
            {
                "beat_id": "opening",
                "utterance_id": "opening-narration",
                "audio": "utterance-opening-narration.wav",
                "duration_seconds": 1.0,
            }
        ],
        skill_version=_skill().sha256,
    )
    output_path = "/workspace/deliverable-job-7-attempt-1.mp4"
    render_receipt = {
        "build_id": index.build_id,
        "skill_version": _skill().sha256,
        "expected_frame_count": render_input.duration_in_frames,
    }
    sandbox = FakeSandboxSession(
        {
            output_path: b"mp4",
            f"{output_path}.render.json": json.dumps(render_receipt).encode(),
        }
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=SimpleNamespace(generation=4))
    )
    saved_kwargs = {}

    async def save(_session, **kwargs):
        saved_kwargs.update(kwargs)
        return ArtifactSaved(
            status="saved",
            artifact_id=22,
            generation=5,
            title="Quarterly update",
            files=[],
        )

    monkeypatch.setattr(
        executor,
        "read_receipt",
        AsyncMock(
            return_value=SimpleNamespace(
                format="video",
                primary_path=output_path,
                primary_sha256="b" * 64,
                visual="clean",
                unavailable_reason=None,
            )
        ),
    )
    monkeypatch.setattr(executor, "save_artifact", save)
    request = executor.VideoJobRequestV1.model_validate(
        {**_job().request, "revision_artifact_id": 22}
    )

    await executor._save_verified(
        session,
        sandbox,
        job=_job(),
        request=request,
        plan=plan,
        render_input=render_input,
        skill=_skill(),
        index=index,
        output_path=output_path,
    )

    assert saved_kwargs["artifact_id"] == 22
    assert saved_kwargs["expected_generation"] == 4
    assert saved_kwargs["files"][0].expected_sha256 == "b" * 64
    runtime = saved_kwargs["extra_metadata"]["video_runtime"]
    assert runtime == {
        "schema_version": 1,
        "build_id": index.build_id,
        "skill_version": _skill().sha256,
        "skill_files": ["SKILL.md"],
        "selected_capability_ids": list(render_input.selected_capability_ids),
        "render_receipt": render_receipt,
    }
