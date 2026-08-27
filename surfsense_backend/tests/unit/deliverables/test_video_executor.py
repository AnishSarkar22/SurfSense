from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import PurePosixPath
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.artifacts.service import ArtifactSaved
from app.deliverables.video import executor
from app.deliverables.video.contracts import CreativeVideoProject
from app.deliverables.video.skill import LoadedVideoSkill
from app.deliverables.video.timeline import NarrationBudget, VideoTimelineDurationError
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


def _project(
    *,
    text: str = "Revenue grew in every region.",
    source: str | None = None,
) -> CreativeVideoProject:
    return CreativeVideoProject.model_validate(
        {
            "narration_cues": ({"cue_id": "opening", "text": text},),
            "language": "en",
            "source_files": (
                {
                    "path": "JobComposition.tsx",
                    "source": source
                    or (
                        'import React from "react";\n'
                        "export const JobComposition = () => <div>Growth</div>;\n"
                    ),
                },
            ),
            "assets": (),
        }
    )


def _skill() -> LoadedVideoSkill:
    return LoadedVideoSkill(content="Author a complete CreativeVideoProject.")


def _capability(capability_id: str, kind: CapabilityKind) -> CapabilityEnvelope:
    return CapabilityEnvelope(
        id=capability_id,
        kind=kind,
        domain="video",
        category="core",
        summary=capability_id,
        tags=("core",),
        tier=CapabilityTier.CORE,
        declaration=(
            {"public_export": "AnimatedBarChart"}
            if kind is CapabilityKind.COMPONENT
            else {}
        ),
        search_text=f"{capability_id} core",
    )


def _index() -> CapabilityIndex:
    return CapabilityIndex(
        schema_version=1,
        build_id="build-12345678",
        runtime_build_id="runtime-123",
        capabilities=(
            _capability("video.renderer.master", CapabilityKind.RENDERER),
            _capability(
                "video.component.animated-bar-chart", CapabilityKind.COMPONENT
            ),
            _capability("font.inter", CapabilityKind.FONT),
        ),
    )


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "source_sha256": "1" * 64,
        "bundle_sha256": "2" * 64,
        "runtime_build_id": "runtime-123",
        "capability_build_id": _index().build_id,
        "imported_capability_ids": ["video.component.animated-bar-chart"],
    }


def _narration(duration: float = 1.0):
    return [
        {
            "cue_id": "opening",
            "audio": "narration-opening.wav",
            "duration_seconds": duration,
        }
    ]


def test_request_and_model_contract_exclude_operational_fields() -> None:
    request = executor.VideoJobRequestV1.model_validate(_job().request)
    assert request.root_thread_id == 11
    with pytest.raises(ValidationError):
        executor.VideoJobRequestV1.model_validate({**_job().request, "version": 2})
    with pytest.raises(ValidationError):
        executor.VideoJobRequestV1.model_validate(
            {**_job().request, "revision_artifact_id": True}
        )

    fields = set(CreativeVideoProject.model_fields)
    assert fields == {"narration_cues", "language", "source_files", "assets"}
    forbidden = {
        "outline",
        "beats",
        "commands",
        "phases",
        "capability_slots",
        "compiler",
        "render",
    }
    assert forbidden.isdisjoint(fields)
    assert not hasattr(executor, "compile_video_plan")
    with pytest.raises(ValidationError):
        CreativeVideoProject.model_validate(
            {**_project().model_dump(), "commands": ["npm install"]}
        )
    with pytest.raises(ValidationError, match="TypeScript or TSX"):
        CreativeVideoProject.model_validate(
            {
                **_project().model_dump(),
                "source_files": (
                    {"path": "JobComposition.tsx", "source": "export const x = 1;"},
                    {"path": "package.json", "source": "{}"},
                ),
            }
        )


def test_disclosure_exposes_full_public_catalog_with_import_names() -> None:
    disclosure = executor._public_capability_disclosure(_index())

    assert disclosure["build_id"] == _index().build_id
    assert disclosure["module"] == "@surfsense/video/capabilities"
    assert [item["id"] for item in disclosure["capabilities"]] == [
        "video.component.animated-bar-chart",
        "font.inter",
    ]
    assert disclosure["capabilities"][0]["export_name"] == "AnimatedBarChart"
    assert disclosure["capabilities"][1]["export_name"] is None


async def test_structured_invocation_uses_billing_compatible_native_schema() -> None:
    captured = {}

    class StructuredLLM:
        async def ainvoke(self, messages):
            captured["messages"] = messages
            return _project().model_dump(mode="json")

    class LLM:
        def with_structured_output(self, schema, **kwargs):
            captured["schema"] = schema
            captured["kwargs"] = kwargs
            return StructuredLLM()

    project = await executor._invoke_structured(
        LLM(),
        skill=_skill(),
        payload={"brief": "Explain growth"},
        model=CreativeVideoProject,
        call_kind="initial_content",
    )

    prompt = json.loads(captured["messages"][-1].content)
    assert project == _project()
    assert captured["schema"]["type"] == "object"
    assert captured["kwargs"] == {"method": "json_schema", "strict": True}
    assert "output_schema" not in prompt
    assert "response_instruction" not in prompt


async def test_materialization_confines_model_source_and_commands() -> None:
    sandbox = FakeSandboxSession()
    workdir = PurePosixPath("/workspace/deliverable-job-7-attempt-1")
    source = '"; touch /tmp/model-command; echo "'

    await executor._materialize_project(
        sandbox, workdir, _project(source=source)
    )

    assert sandbox.writes == {
        f"{workdir}/source/JobComposition.tsx": source.encode()
    }
    assert len(sandbox.commands) == 1
    assert source not in sandbox.commands[0]
    assert "/tmp/model-command" not in sandbox.commands[0]
    assert all(path.startswith(f"{workdir}/source/") for path in sandbox.writes)


async def test_materialization_rejects_unstaged_assets_before_writing() -> None:
    sandbox = FakeSandboxSession()
    project = CreativeVideoProject.model_validate(
        {
            **_project().model_dump(),
            "assets": (
                {"id": "remote", "path": "assets/remote.png", "kind": "image"},
            ),
        }
    )

    with pytest.raises(ValueError, match="was not staged"):
        await executor._materialize_project(
            sandbox,
            PurePosixPath("/workspace/deliverable-job-7-attempt-1"),
            project,
        )

    assert sandbox.commands == []
    assert sandbox.writes == {}


async def test_executor_starts_tts_and_bundle_together_and_reuses_job(
    monkeypatch,
) -> None:
    sandbox = FakeSandboxSession()
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    tts_started = asyncio.Event()
    bundle_started = asyncio.Event()
    model_calls: list[type] = []

    class Registry:
        async def get_session(self, owner, workspace_id, *, profile):
            assert (owner, workspace_id) == ("deliverable-job-7-attempt-1", 3)
            assert profile is SandboxResourceProfile.VIDEO_RENDER
            return sandbox

    async def heartbeat(*_args, **_kwargs):
        return SimpleNamespace(id=7)

    async def model_call(*_args, **kwargs):
        model_calls.append(kwargs["model"])
        return _project()

    async def tts(*_args, **_kwargs):
        tts_started.set()
        await asyncio.wait_for(bundle_started.wait(), timeout=1)
        return _narration()

    async def bundle(*_args, **_kwargs):
        bundle_started.set()
        await asyncio.wait_for(tts_started.wait(), timeout=1)
        return _manifest()

    render_input = executor._trusted_render_input(
        _project(),
        _narration(),
        index=_index(),
        manifest=_manifest(),
    )
    commands: list[str] = []

    async def preflight(_sandbox, workdir, props_path, *, job_id):
        commands.append(executor._render_command(workdir, "--preflight", props_path))
        return None

    async def stills(_sandbox, *, workdir, props_path, **_kwargs):
        commands.append(
            executor._render_command(workdir, "--stills", props_path, workdir / "stills")
        )
        return None

    async def render(_sandbox, workdir, props_path, output_path):
        commands.append(executor._render_command(workdir, props_path, output_path))

    async def save(*_args, **_kwargs):
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
    monkeypatch.setattr(executor, "_materialize_project", AsyncMock())
    monkeypatch.setattr(executor, "_timed_tts", tts)
    monkeypatch.setattr(executor, "_timed_bundle", bundle)
    monkeypatch.setattr(
        executor, "_finalize_job_assets", AsyncMock(return_value=_manifest())
    )
    monkeypatch.setattr(executor, "_trusted_render_input", lambda *_a, **_k: render_input)
    monkeypatch.setattr(executor, "_timed_preflight", preflight)
    monkeypatch.setattr(executor, "_timed_stills_review", stills)
    monkeypatch.setattr(executor, "_render", render)
    monkeypatch.setattr(
        executor,
        "get_vision_llm",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        executor,
        "verify_artifact",
        AsyncMock(return_value=SimpleNamespace(verified=True, findings=())),
    )
    monkeypatch.setattr(executor, "_save_verified", save)
    monkeypatch.setattr(executor, "_cleanup_attempt", AsyncMock())

    result = await executor.execute_video_deliverable(session, _job(), object())

    assert result.cue_count == 1
    assert result.repair_count == 0
    assert model_calls == [CreativeVideoProject]
    assert len(commands) == 3
    assert all(
        "--job-dir /workspace/deliverable-job-7-attempt-1/job" in command
        for command in commands
    )
    assert not any("bundle-job" in command for command in commands)


async def test_narration_repair_changes_text_only_and_resynthesizes_changed_cues(
    monkeypatch,
) -> None:
    rewrite = executor.NarrationRewrite.model_validate(
        {"cues": ({"cue_id": "opening", "text": "Growth continued."},)}
    )
    invoke = AsyncMock(return_value=rewrite)
    monkeypatch.setattr(executor, "_invoke_structured", invoke)

    repaired, requests = await executor._request_narration_repair(
        object(),
        skill=_skill(),
        project=_project(),
        duration_error=VideoTimelineDurationError(
            compiled_frames=6000,
            suggested_narration_budgets=(
                NarrationBudget(
                    cue_id="opening",
                    max_seconds=2,
                    max_words=3,
                ),
            ),
        ),
    )

    assert repaired.narration_cues[0].cue_id == "opening"
    assert repaired.narration_cues[0].text == "Growth continued."
    assert repaired.source_files == _project().source_files
    assert repaired.language == _project().language
    assert requests == [
        {
            "cue_id": "opening",
            "transcript": "Growth continued.",
            "max_words": 3,
        }
    ]
    assert invoke.await_args.kwargs["model"] is executor.NarrationRewrite


async def test_visual_repair_protects_cue_identity_text_and_language(
    monkeypatch,
) -> None:
    changed = _project(text="Changed narration.")
    monkeypatch.setattr(executor, "_invoke_structured", AsyncMock(return_value=changed))

    with pytest.raises(ValueError, match="protected cue"):
        await executor._repair_project(
            object(),
            skill=_skill(),
            project=_project(),
            findings="Headline clips",
            visual_only=True,
        )


async def test_content_repair_rebundles_changed_source_exactly_once(
    monkeypatch,
) -> None:
    sandbox = FakeSandboxSession()
    before = _project()
    repaired = _project(source="export const JobComposition = () => null;\n")
    bundle = AsyncMock(return_value=_manifest())
    finalize = AsyncMock(return_value=_manifest())
    materialize = AsyncMock()
    monkeypatch.setattr(
        executor, "_repair_project", AsyncMock(return_value=repaired)
    )
    monkeypatch.setattr(executor, "_materialize_project", materialize)
    monkeypatch.setattr(executor, "_timed_bundle", bundle)
    monkeypatch.setattr(executor, "_finalize_job_assets", finalize)

    result = await executor._content_repair(
        object(),
        sandbox=sandbox,
        skill=_skill(),
        before=before,
        narration=_narration(),
        findings="TypeScript compilation failed",
        visual_only=False,
        workdir=PurePosixPath("/workspace/deliverable-job-7-attempt-1"),
        index=_index(),
        job_id=7,
    )

    assert result[0] == repaired
    materialize.assert_awaited_once()
    bundle.assert_awaited_once()
    finalize.assert_awaited_once()


def test_backend_commands_are_fixed_and_render_uses_prepared_job(monkeypatch) -> None:
    workdir = PurePosixPath("/workspace/deliverable-job-7-attempt-1")
    monkeypatch.setattr(executor.app_config, "VIDEO_SANDBOX_FRAME_CONCURRENCY", 2)

    assert executor._bundle_command(workdir) == (
        "cd -- /workspace/deliverable-job-7-attempt-1 && "
        "node scripts/bundle-job.mjs "
        "--source-dir /workspace/deliverable-job-7-attempt-1/source "
        "--out-dir /workspace/deliverable-job-7-attempt-1/job"
    )
    assert executor._finalize_command(workdir) == (
        "cd -- /workspace/deliverable-job-7-attempt-1 && "
        "node scripts/finalize-job.mjs "
        "--job-dir /workspace/deliverable-job-7-attempt-1/job "
        "--public-dir /workspace/deliverable-job-7-attempt-1/public"
    )
    assert executor._render_command(
        workdir, "--preflight", workdir / "props.json"
    ) == (
        "cd -- /workspace/deliverable-job-7-attempt-1 && "
        "VIDEO_SANDBOX_FRAME_CONCURRENCY=2 node render.mjs "
        "--job-dir /workspace/deliverable-job-7-attempt-1/job "
        "--preflight /workspace/deliverable-job-7-attempt-1/props.json"
    )


async def test_phase_timings_are_structured(caplog, monkeypatch) -> None:
    recorded = []
    monkeypatch.setattr(
        executor.ot_metrics,
        "record_perf_elapsed",
        lambda duration_ms, *, label: recorded.append((duration_ms, label)),
    )
    caplog.set_level(logging.INFO, logger=executor.__name__)
    async with executor._phase_timing("authoring", job_id=7):
        await asyncio.sleep(0)

    record = next(
        record for record in caplog.records if record.msg == "video_executor_phase"
    )
    assert record.video_phase == "authoring"
    assert record.video_job_id == 7
    assert record.video_phase_status == "ok"
    assert record.elapsed_seconds >= 0
    assert recorded[0][0] >= 0
    assert recorded[0][1] == "video_executor.authoring"


async def test_revision_save_checks_receipt_hashes_and_persists_provenance(
    monkeypatch,
) -> None:
    project = _project()
    manifest = _manifest()
    render_input = executor._trusted_render_input(
        project,
        _narration(),
        index=_index(),
        manifest=manifest,
    )
    output_path = "/workspace/deliverable-job-7-attempt-1.mp4"
    render_receipt = {
        "schema_version": 1,
        "build_id": _index().build_id,
        "capability_build_id": _index().build_id,
        "runtime_build_id": _index().runtime_build_id,
        "input_sha256": hashlib.sha256(
            (
                render_input.model_dump_json(by_alias=True, exclude_none=True) + "\n"
            ).encode()
        ).hexdigest(),
        "expected_frame_count": render_input.duration_in_frames,
        "expected_duration_seconds": (
            render_input.duration_in_frames / render_input.fps
        ),
        "source_sha256": manifest["source_sha256"],
        "bundle_sha256": manifest["bundle_sha256"],
        "selected_capability_ids": list(render_input.selected_capability_ids),
        "imported_capability_ids": manifest["imported_capability_ids"],
        "sample_frames": [
            sample.model_dump(mode="json") for sample in render_input.sample_frames
        ],
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
        project=project,
        render_input=render_input,
        index=_index(),
        manifest=manifest,
        output_path=output_path,
    )

    assert saved_kwargs["artifact_id"] == 22
    assert saved_kwargs["expected_generation"] == 4
    assert saved_kwargs["files"][0].expected_sha256 == "b" * 64
    runtime = saved_kwargs["extra_metadata"]["video_runtime"]
    assert runtime["cue_ids"] == ["opening"]
    assert runtime["source_files"] == ["JobComposition.tsx"]
    assert runtime["source_sha256"] == "1" * 64
    assert runtime["bundle_sha256"] == "2" * 64
    assert runtime["imported_capability_ids"] == [
        "video.component.animated-bar-chart"
    ]


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
