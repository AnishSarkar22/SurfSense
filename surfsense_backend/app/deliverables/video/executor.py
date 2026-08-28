"""Queued orchestration for agent-authored, backend-confined video projects."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shlex
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.chat.multi_agent_chat.subagents.builtins.deliverables.tools.sandbox import (
    _run_bash,
)
from app.artifacts import ArtifactFileStreamInput, save_artifact
from app.artifacts.persistence import Artifact
from app.artifacts.verification.receipt import read_receipt, receipt_path
from app.artifacts.verification.service import verify_artifact
from app.config import config as app_config
from app.db import DeliverableJob
from app.deliverables.jobs.policy import VIDEO_KIND, VIDEO_SPEC
from app.deliverables.jobs.service import heartbeat_deliverable_job
from app.deliverables.video.contracts import CreativeVideoProject, VideoRenderInput
from app.deliverables.video.narration import (
    NarrationUtterance,
    merge_narration_audio,
    synthesize_narration,
)
from app.deliverables.video.skill import LoadedVideoSkill, load_video_skill
from app.deliverables.video.structured_output import provider_json_schema
from app.deliverables.video.timeline import (
    VideoTimelineDurationError,
    build_video_render_input,
)
from app.observability import metrics as ot_metrics
from app.sandbox import SandboxResourceProfile, SandboxSession, get_registry
from app.sandbox.capabilities import (
    build_public_capability_catalog,
    load_capability_index,
    retrieve_capability_ids,
)
from app.sandbox.capabilities.schema import (
    CapabilityId,
    CapabilityIndex,
    CapabilityKind,
)

_MAX_BRIEF_CHARS = 16_000
_MAX_SOURCE_REFERENCES = 25
_MAX_SOURCE_REFERENCE_CHARS = 1_000
_MODEL_TIMEOUT_SECONDS = 10 * 60
_LIVENESS_INTERVAL_SECONDS = min(60, app_config.SANDBOX_IDLE_TTL_SECONDS / 3)
_FINDINGS_CHARS = 16_000
_STAGED_ASSETS = (
    {"id": "surfsense-icon", "path": "icon-128.svg", "kind": "svg"},
)
logger = logging.getLogger(__name__)


class DeliverableJobCancellationError(Exception):
    """Raised when the persisted lifecycle no longer permits executor work."""


async def _await_with_liveness[T](
    work: Awaitable[T],
    *,
    pulse: Callable[[], Awaitable[None]],
    interval_seconds: float,
) -> T:
    task = asyncio.ensure_future(work)
    try:
        while not task.done():
            done, _ = await asyncio.wait({task}, timeout=interval_seconds)
            if task in done:
                break
            await pulse()
        return await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


class VideoJobRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1]
    brief: Annotated[str, Field(min_length=1, max_length=_MAX_BRIEF_CHARS)]
    source_references: Annotated[
        list[
            Annotated[str, Field(min_length=1, max_length=_MAX_SOURCE_REFERENCE_CHARS)]
        ],
        Field(max_length=_MAX_SOURCE_REFERENCES),
    ] = Field(default_factory=list)
    revision_artifact_id: Annotated[int, Field(gt=0)] | None = None
    root_thread_id: Annotated[int, Field(gt=0)]

    @field_validator("brief")
    @classmethod
    def normalized_brief(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("brief must not be empty")
        return normalized

    @field_validator("source_references")
    @classmethod
    def safe_source_references(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.split()) for value in values]
        if any(not value or "\x00" in value for value in normalized):
            raise ValueError("source references must be non-empty text")
        if len(normalized) != len(set(normalized)):
            raise ValueError("source references must be unique")
        return normalized


class _NarrationRewriteCue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    cue_id: Annotated[
        str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    ]
    text: Annotated[str, Field(min_length=1, max_length=8000)]

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("rewritten cue text must not be empty")
        return normalized


class NarrationRewrite(BaseModel):
    """The only model repair contract that is not a complete video project."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    cues: Annotated[
        tuple[_NarrationRewriteCue, ...],
        Field(min_length=1, max_length=VIDEO_SPEC.max_narration_cues),
    ]


class PreparedJobManifest(BaseModel):
    """Trusted result of source validation and one per-revision bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    source_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    bundle_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    runtime_build_id: Annotated[
        str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    ]
    capability_build_id: Annotated[
        str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    ]
    imported_capability_ids: Annotated[
        tuple[CapabilityId, ...], Field(max_length=100)
    ] = ()

    @field_validator("imported_capability_ids")
    @classmethod
    def unique_sorted_capability_ids(
        cls, values: tuple[CapabilityId, ...]
    ) -> tuple[CapabilityId, ...]:
        if tuple(sorted(set(values))) != values:
            raise ValueError("imported capability IDs must be sorted and unique")
        return values


def _validated_job_manifest(value: object) -> PreparedJobManifest:
    return PreparedJobManifest.model_validate_json(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    )


class VideoExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: int
    generation: int
    title: str
    output_path: str
    cue_count: int
    duration_seconds: float
    repair_count: Annotated[int, Field(ge=0, le=VIDEO_SPEC.max_repair_cycles)]


def video_sandbox_owner(job_id: int, attempt_count: int) -> str:
    return f"deliverable-job-{job_id}-attempt-{attempt_count}"


@asynccontextmanager
async def _phase_timing(phase: str, *, job_id: int):
    started = time.perf_counter()
    outcome = "ok"
    try:
        yield
    except BaseException:
        outcome = "error"
        raise
    finally:
        elapsed_seconds = time.perf_counter() - started
        logger.info(
            "video_executor_phase",
            extra={
                "video_phase": phase,
                "video_job_id": job_id,
                "video_phase_status": outcome,
                "elapsed_seconds": elapsed_seconds,
            },
        )
        ot_metrics.record_perf_elapsed(
            elapsed_seconds * 1000,
            label=f"video_executor.{phase.replace('/', '_')}",
        )


async def execute_video_deliverable(
    session: AsyncSession,
    job: DeliverableJob,
    llm,
) -> VideoExecutionResult:
    """Author once, prepare one trusted bundle, render, verify, and persist."""

    if not app_config.VIDEO_SANDBOX_RENDERING_ENABLED:
        raise RuntimeError("static sandbox video rendering is disabled")
    request = VideoJobRequestV1.model_validate(job.request)
    if job.kind != VIDEO_KIND:
        raise ValueError("video executor only accepts video deliverable jobs")
    if job.thread_id is None or request.root_thread_id != job.thread_id:
        raise ValueError("queued video request must name its root thread")

    owner = video_sandbox_owner(job.id, job.attempt_count)
    workdir = PurePosixPath(
        f"/workspace/deliverable-job-{job.id}-attempt-{job.attempt_count}"
    )
    output_path = f"{workdir}.mp4"
    registry = await get_registry()
    sandbox = await registry.get_session(
        owner,
        job.workspace_id,
        profile=SandboxResourceProfile.VIDEO_RENDER,
    )

    async def heartbeat(phase: str, progress: int) -> None:
        await _heartbeat(
            session,
            job.id,
            phase,
            progress,
            task_id=job.celery_task_id,
        )

    async def pulse(phase: str, progress: int) -> None:
        await heartbeat(phase, progress)
        await registry.keep_alive(
            owner,
            profile=SandboxResourceProfile.VIDEO_RENDER,
        )

    await heartbeat("preparing", 5)
    await _stage_runtime(sandbox, workdir)
    skill, index = await asyncio.gather(
        load_video_skill(sandbox),
        load_capability_index(sandbox, image_digest=None),
    )
    if index.runtime_build_id is None:
        raise ValueError("video capability index lacks a runtime build identity")
    disclosed_ids = retrieve_capability_ids(index, f"{job.title}\n{request.brief}")
    disclosure = build_public_capability_catalog(index, selected_ids=disclosed_ids)

    await heartbeat("authoring", 15)
    async with _phase_timing("authoring", job_id=job.id):
        project = await _invoke_structured(
            llm,
            skill=skill,
            payload={
                "request_title": job.title,
                "brief": request.brief,
                "source_references": _source_labels(request.source_references),
                "revision_artifact_id": request.revision_artifact_id,
                "public_capabilities": disclosure,
                "available_assets": list(_STAGED_ASSETS),
                "technical_limits": _technical_limits(),
                "instructions": (
                    "Return the complete CreativeVideoProject. Author only source files, "
                    "narration cues, language, and declared assets. Never return commands, "
                    "render phases, or artifact operations."
                ),
            },
            model=CreativeVideoProject,
            call_kind="initial_content",
        )
    await _materialize_project(sandbox, workdir, project)

    await heartbeat("preparing_content", 30)
    narration_task = asyncio.create_task(
        _timed_tts(sandbox, workdir, project, request, job)
    )
    bundle_task = asyncio.create_task(_timed_bundle(sandbox, workdir, job.id))
    narration_result, bundle_result = await _await_with_liveness(
        asyncio.gather(narration_task, bundle_task, return_exceptions=True),
        pulse=lambda: pulse("preparing_content", 30),
        interval_seconds=_LIVENESS_INTERVAL_SECONDS,
    )
    if isinstance(narration_result, BaseException):
        raise narration_result

    repairs = 0
    if isinstance(bundle_result, BaseException):
        if VIDEO_SPEC.max_repair_cycles < 1:
            raise bundle_result
        project = await _repair_project(
            llm,
            skill=skill,
            project=project,
            findings=str(bundle_result),
        )
        repairs = 1
        await _materialize_project(sandbox, workdir, project)
        bundle_result = await _timed_bundle(sandbox, workdir, job.id)
    narration = narration_result
    manifest = await _finalize_job_assets(sandbox, workdir, job.id)

    try:
        render_input = _trusted_render_input(
            project, narration, index=index, manifest=manifest
        )
    except VideoTimelineDurationError as exc:
        await heartbeat("repairing_narration", 45)
        project, replacements = await _request_narration_repair(
            llm, skill=skill, project=project, duration_error=exc
        )
        async with _phase_timing("TTS", job_id=job.id):
            replacement_audio = await _await_with_liveness(
                synthesize_narration(
                    replacements,
                    str(workdir),
                    workspace_id=job.workspace_id,
                    thread_id=request.root_thread_id,
                    session=sandbox,
                    language=project.language,
                ),
                pulse=lambda: pulse("repairing_narration", 45),
                interval_seconds=_LIVENESS_INTERVAL_SECONDS,
            )
        narration = merge_narration_audio(narration, replacement_audio)
        manifest = await _finalize_job_assets(sandbox, workdir, job.id)
        render_input = _trusted_render_input(
            project, narration, index=index, manifest=manifest
        )

    props_path = await _write_render_input(sandbox, workdir, render_input)
    await heartbeat("rendering", 55)
    async with _phase_timing("render", job_id=job.id):
        await _render(sandbox, workdir, props_path, output_path)

    await heartbeat("verifying", 90)
    async with _phase_timing("verification", job_id=job.id):
        verification = await verify_artifact(
            sandbox,
            output_path,
            workspace_id=job.workspace_id,
            vision_llm=None,
        )
        if not verification.verified:
            raise RuntimeError(
                "video verification failed: " + "; ".join(verification.findings)
            )

    await heartbeat("saving", 95)
    async with _phase_timing("persistence", job_id=job.id):
        saved = await _save_verified(
            session,
            sandbox,
            job=job,
            request=request,
            project=project,
            render_input=render_input,
            index=index,
            manifest=manifest,
            output_path=output_path,
        )
    async with _phase_timing("cleanup", job_id=job.id):
        await _cleanup_attempt(sandbox, workdir, output_path)
    return VideoExecutionResult(
        artifact_id=saved.artifact_id,
        generation=saved.generation,
        title=saved.title,
        output_path=output_path,
        cue_count=len(project.narration_cues),
        duration_seconds=render_input.duration_in_frames / render_input.fps,
        repair_count=repairs,
    )


async def _heartbeat(
    session: AsyncSession,
    job_id: int,
    phase: str,
    progress: int,
    *,
    task_id: str | None = None,
) -> None:
    updated = await heartbeat_deliverable_job(
        session,
        job_id,
        phase=phase,
        progress=progress,
        task_id=task_id,
    )
    if updated is None:
        await session.rollback()
        raise DeliverableJobCancellationError
    await session.commit()


async def _stage_runtime(sandbox: SandboxSession, workdir: PurePosixPath) -> None:
    quoted = shlex.quote(str(workdir))
    await _run_checked(
        sandbox,
        f"rm -rf -- {quoted} && mkdir -p -- {quoted} && "
        f"cp -a --reflink=auto /opt/surfsense/video-runtime/. {quoted}/ && "
        f"mkdir -p -- {quoted}/source {quoted}/public && rm -f -- {quoted}/cancel",
        "stage prebuilt video runtime",
    )


def _source_labels(references: list[str]) -> list[dict[str, str]]:
    return [
        {"label": f"Source {index}", "reference": reference}
        for index, reference in enumerate(references, start=1)
    ]


def _technical_limits() -> dict[str, object]:
    return {
        "canvas": {"width": 1920, "height": 1080},
        "fps": 30,
        "target_duration_seconds": VIDEO_SPEC.max_duration_seconds,
        "hard_max_duration_seconds": VIDEO_SPEC.hard_max_duration_seconds,
        "max_narration_cues": VIDEO_SPEC.max_narration_cues,
        "max_source_files": 32,
        "max_source_bytes": 256 * 1024,
        "source_root": "source",
        "public_asset_root": "public",
        "required_entrypoint": {
            "path": "JobComposition.tsx",
            "named_export": "JobComposition",
            "accepts_props": False,
        },
        "allowed_imports": [
            "react",
            "remotion",
            "@remotion/fonts",
            "@remotion/media",
            "@remotion/transitions",
            "@surfsense/video",
            "@surfsense/video/capabilities",
        ],
        "forbidden_runtime_apis": [
            "commands",
            "dynamic imports",
            "network access",
            "wall-clock time",
            "randomness",
        ],
    }


async def _invoke_structured(
    llm,
    *,
    skill: LoadedVideoSkill,
    payload: dict,
    model: type[BaseModel],
    call_kind: Literal["initial_content", "source_repair", "narration_repair"],
):
    scope = getattr(llm, "for_queued_video_call", None)
    call_llm = scope(call_kind) if callable(scope) else llm
    structured_llm = call_llm.with_structured_output(
        provider_json_schema(model),
        method="json_schema",
        strict=True,
    )
    messages = [SystemMessage(content=skill.content)]
    if call_kind != "narration_repair":
        messages.append(
            SystemMessage(
                content=(
                    "The following TypeScript is the exact @surfsense/video public "
                    "authoring contract. Use only these exports and field names.\n\n"
                    f"```typescript\n{skill.authoring_contract}\n```"
                )
            )
        )
    messages.append(
        HumanMessage(content=json.dumps(payload, ensure_ascii=False, sort_keys=True))
    )
    result = await asyncio.wait_for(
        structured_llm.ainvoke(messages),
        timeout=_MODEL_TIMEOUT_SECONDS,
    )
    return model.model_validate_json(json.dumps(result, ensure_ascii=False))


async def _materialize_project(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    project: CreativeVideoProject,
) -> None:
    """Write validated model content only to its two fixed backend-owned roots."""

    available = {
        (asset["id"], asset["path"], asset["kind"]) for asset in _STAGED_ASSETS
    }
    declared = {(asset.id, asset.path, asset.kind) for asset in project.assets}
    if not declared.issubset(available):
        raise ValueError("video project references an asset that was not staged")
    source_root = workdir / "source"
    source_directories = sorted(
        {
            str(source_root / PurePosixPath(source_file.path).parent)
            for source_file in project.source_files
            if PurePosixPath(source_file.path).parent != PurePosixPath(".")
        }
    )
    directories = " ".join(
        shlex.quote(path) for path in (str(source_root), *source_directories)
    )
    await _run_checked(
        sandbox,
        f"rm -rf -- {shlex.quote(str(source_root))} "
        f"{shlex.quote(str(workdir / 'job'))} && "
        f"mkdir -p -- {directories} "
        f"{shlex.quote(str(workdir / 'public'))}",
        "reset job-authored video source",
    )
    for source_file in project.source_files:
        await sandbox.write_file(
            str(workdir / "source" / source_file.path), source_file.source.encode()
        )


async def _timed_tts(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    project: CreativeVideoProject,
    request: VideoJobRequestV1,
    job: DeliverableJob,
):
    async with _phase_timing("TTS", job_id=job.id):
        return await synthesize_narration(
            [
                {"cue_id": cue.cue_id, "transcript": cue.text}
                for cue in project.narration_cues
            ],
            str(workdir),
            workspace_id=job.workspace_id,
            thread_id=request.root_thread_id,
            session=sandbox,
            language=project.language,
        )


def _bundle_command(workdir: PurePosixPath) -> str:
    return (
        f"cd -- {shlex.quote(str(workdir))} && node scripts/bundle-job.mjs "
        f"--source-dir {shlex.quote(str(workdir / 'source'))} "
        f"--out-dir {shlex.quote(str(workdir / 'job'))}"
    )


async def _timed_bundle(
    sandbox: SandboxSession, workdir: PurePosixPath, job_id: int
) -> dict:
    async with _phase_timing("source validation/bundle", job_id=job_id):
        await _run_checked(
            sandbox, _bundle_command(workdir), "validate and bundle video source"
        )
        try:
            manifest = json.loads(
                (await sandbox.read_file(str(workdir / "job" / "job.json"))).decode()
            )
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("prepared video job manifest is missing or invalid") from exc
        return _validated_job_manifest(manifest).model_dump(mode="json")


def _finalize_command(workdir: PurePosixPath) -> str:
    return (
        f"cd -- {shlex.quote(str(workdir))} && node scripts/finalize-job.mjs "
        f"--job-dir {shlex.quote(str(workdir / 'job'))} "
        f"--public-dir {shlex.quote(str(workdir / 'public'))}"
    )


async def _finalize_job_assets(
    sandbox: SandboxSession, workdir: PurePosixPath, job_id: int
) -> dict:
    async with _phase_timing("asset staging", job_id=job_id):
        await _run_checked(
            sandbox,
            _finalize_command(workdir),
            "stage and seal video assets",
        )
        return await _read_job_manifest(sandbox, workdir)


def _trusted_render_input(
    project: CreativeVideoProject,
    narration,
    *,
    index: CapabilityIndex,
    manifest: dict,
) -> VideoRenderInput:
    prepared = _validated_job_manifest(manifest)
    if prepared.capability_build_id != index.build_id:
        raise ValueError("prepared job capability build does not match loaded index")
    if (
        index.runtime_build_id is None
        or prepared.runtime_build_id != index.runtime_build_id
    ):
        raise ValueError("prepared job runtime build does not match loaded index")
    imported = prepared.imported_capability_ids
    unknown = set(imported) - set(index.by_id())
    if unknown:
        raise ValueError(f"prepared job imported unknown capabilities: {sorted(unknown)}")
    selected_capability_ids = {
        "video.renderer.master",
        *imported,
        *(
            capability.id
            for capability in index.capabilities
            if capability.kind is CapabilityKind.FONT
        ),
    }
    return build_video_render_input(
        project,
        narration,
        build_id=index.build_id,
        selected_capability_ids=selected_capability_ids,
    )


async def _request_narration_repair(
    llm,
    *,
    skill: LoadedVideoSkill,
    project: CreativeVideoProject,
    duration_error: VideoTimelineDurationError,
) -> tuple[CreativeVideoProject, list[NarrationUtterance]]:
    rewrite = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "diagnostics": {
                "max_frames": duration_error.max_frames,
                "compiled_frames": duration_error.compiled_frames,
                "overflow_frames": duration_error.overflow_frames,
            },
            "targets": [
                {
                    "cue_id": target.cue_id,
                    "target_seconds": target.target_seconds,
                    "target_words": target.target_words,
                }
                for target in duration_error.suggested_narration_targets
            ],
            "narration_cues": [
                {"cue_id": cue.cue_id, "text": cue.text}
                for cue in project.narration_cues
            ],
            "instructions": (
                "Return cue text only. Preserve every cue_id exactly and in order. "
                "Rewrite only cues that need shortening. Return no source, visual, "
                "language, timing, command, or operational fields. Aim for the "
                "per-cue targets; measured audio duration determines acceptance."
            ),
        },
        model=NarrationRewrite,
        call_kind="narration_repair",
    )
    original = {cue.cue_id: cue for cue in project.narration_cues}
    if [cue.cue_id for cue in rewrite.cues] != [
        cue.cue_id for cue in project.narration_cues
    ]:
        raise ValueError("narration repair changed protected cue identity or order")
    replacements: list[NarrationUtterance] = []
    rewritten: dict[str, str] = {}
    for cue in rewrite.cues:
        if cue.text == original[cue.cue_id].text:
            continue
        rewritten[cue.cue_id] = cue.text
        replacements.append(
            {
                "cue_id": cue.cue_id,
                "transcript": cue.text,
            }
        )
    if not replacements:
        raise ValueError("narration repair did not change any cue")
    return (
        project.model_copy(
            update={
                "narration_cues": tuple(
                    cue.model_copy(
                        update={"text": rewritten.get(cue.cue_id, cue.text)}
                    )
                    for cue in project.narration_cues
                )
            }
        ),
        replacements,
    )


async def _repair_project(
    llm,
    *,
    skill: LoadedVideoSkill,
    project: CreativeVideoProject,
    findings: str | list[dict[str, object]],
) -> CreativeVideoProject:
    repaired = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "findings": (
                findings[-_FINDINGS_CHARS:]
                if isinstance(findings, str)
                else findings
            ),
            "current_project": project.model_dump(mode="json"),
            "protected_fields": [
                "narration_cues.cue_id",
                "narration_cues.text",
                "language",
            ],
            "instructions": (
                "Return a complete corrected CreativeVideoProject. Change source/content "
                "only as needed. Never return commands or operational phases."
            ),
        },
        model=CreativeVideoProject,
        call_kind="source_repair",
    )
    if (
        repaired.language != project.language
        or [(cue.cue_id, cue.text) for cue in repaired.narration_cues]
        != [(cue.cue_id, cue.text) for cue in project.narration_cues]
    ):
        raise ValueError("source repair changed protected cue identity, text, or language")
    return repaired


async def _read_job_manifest(
    sandbox: SandboxSession, workdir: PurePosixPath
) -> dict:
    try:
        document = json.loads(
            (await sandbox.read_file(str(workdir / "job" / "job.json"))).decode()
        )
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("prepared video job manifest is missing or invalid") from exc
    return _validated_job_manifest(document).model_dump(mode="json")


async def _write_render_input(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    render_input: VideoRenderInput,
) -> str:
    path = str(workdir / "props.json")
    await sandbox.write_file(
        path,
        (render_input.model_dump_json(by_alias=True, exclude_none=True) + "\n").encode(),
    )
    return path


async def _render(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    props_path: str,
    output_path: str,
) -> None:
    await _run_checked(
        sandbox,
        _render_command(workdir, props_path, output_path),
        "render video",
        video=True,
    )


def _render_command(
    workdir: PurePosixPath,
    props_path: str | PurePosixPath,
    output_path: str,
) -> str:
    return (
        f"cd -- {shlex.quote(str(workdir))} && "
        f"VIDEO_SANDBOX_FRAME_CONCURRENCY="
        f"{app_config.VIDEO_SANDBOX_FRAME_CONCURRENCY} node render.mjs "
        f"--job-dir {shlex.quote(str(workdir / 'job'))} "
        f"{shlex.quote(str(props_path))} {shlex.quote(output_path)}"
    )


async def _run_checked(
    sandbox: SandboxSession,
    command: str,
    operation: str,
    *,
    video: bool = False,
) -> None:
    result = (
        await _run_bash(sandbox, command)
        if video
        else await sandbox.run_command(command)
    )
    if not result.ok:
        raise RuntimeError(f"Could not {operation}: {result.output[-_FINDINGS_CHARS:]}")


async def _cleanup_attempt(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    output_path: str,
) -> None:
    paths = (
        str(workdir),
        output_path,
        f"{output_path}.render.json",
        receipt_path(output_path),
    )
    try:
        result = await sandbox.run_command(
            f"rm -rf -- {' '.join(shlex.quote(path) for path in paths)}"
        )
        if not result.ok:
            raise RuntimeError(result.output[-4000:])
    except Exception:
        logger.warning("Could not clean persisted video attempt files", exc_info=True)


def _markdown(project: CreativeVideoProject, title: str) -> str:
    sections = [
        f"## {cue.cue_id}\n\n**Narration:** {cue.text}"
        for cue in project.narration_cues
    ]
    return f"# {title}\n\n" + "\n\n".join(sections)


async def _save_verified(
    session: AsyncSession,
    sandbox: SandboxSession,
    *,
    job: DeliverableJob,
    request: VideoJobRequestV1,
    project: CreativeVideoProject,
    render_input: VideoRenderInput,
    index: CapabilityIndex,
    manifest: dict,
    output_path: str,
):
    receipt = await read_receipt(
        sandbox,
        app_config.SECRET_KEY,
        workspace_id=job.workspace_id,
        primary_path=output_path,
    )
    if receipt.format != "video" or receipt.primary_path != output_path:
        raise ValueError("video save requires verification for the exact MP4")
    try:
        render_receipt = json.loads(
            (await sandbox.read_file(f"{output_path}.render.json")).decode()
        )
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("video render receipt is missing or unreadable") from exc
    prepared = _validated_job_manifest(manifest)
    serialized_input = (
        render_input.model_dump_json(by_alias=True, exclude_none=True) + "\n"
    ).encode()
    expected_provenance = {
        "schema_version": render_input.schema_version,
        "build_id": index.build_id,
        "capability_build_id": index.build_id,
        "runtime_build_id": prepared.runtime_build_id,
        "input_sha256": hashlib.sha256(serialized_input).hexdigest(),
        "expected_frame_count": render_input.duration_in_frames,
        "expected_duration_seconds": (
            render_input.duration_in_frames / render_input.fps
        ),
        "source_sha256": prepared.source_sha256,
        "bundle_sha256": prepared.bundle_sha256,
        "selected_capability_ids": list(render_input.selected_capability_ids),
        "imported_capability_ids": list(prepared.imported_capability_ids),
        "sample_frames": [
            sample.model_dump(mode="json") for sample in render_input.sample_frames
        ],
    }
    if any(render_receipt.get(key) != value for key, value in expected_provenance.items()):
        raise ValueError("video render receipt does not match the prepared job")

    expected_generation = None
    if request.revision_artifact_id is not None:
        artifact = await session.scalar(
            select(Artifact).where(
                Artifact.id == request.revision_artifact_id,
                Artifact.workspace_id == job.workspace_id,
                Artifact.format == "video",
            )
        )
        if artifact is None:
            raise ValueError("revision video artifact does not exist in this workspace")
        expected_generation = artifact.generation

    return await save_artifact(
        session,
        workspace_id=job.workspace_id,
        thread_id=request.root_thread_id,
        tool_call_id=job.tool_call_id,
        title=job.title,
        markdown_representation=_markdown(project, job.title),
        files=[
            ArtifactFileStreamInput(
                chunks=sandbox.read_file_stream(output_path),
                filename=PurePosixPath(output_path).name,
                mime_type="video/mp4",
                expected_sha256=receipt.primary_sha256,
            )
        ],
        artifact_id=request.revision_artifact_id,
        expected_generation=expected_generation,
        extra_metadata={
            "verification": {
                "verified": receipt.visual != "unavailable",
                "reason": receipt.unavailable_reason,
                "sha256": receipt.primary_sha256,
            },
            "video_runtime": {
                "schema_version": render_input.schema_version,
                "build_id": index.build_id,
                "cue_ids": [cue.cue_id for cue in project.narration_cues],
                "source_files": [source.path for source in project.source_files],
                "source_sha256": prepared.source_sha256,
                "bundle_sha256": prepared.bundle_sha256,
                "runtime_build_id": prepared.runtime_build_id,
                "capability_build_id": prepared.capability_build_id,
                "imported_capability_ids": list(prepared.imported_capability_ids),
                "selected_capability_ids": list(render_input.selected_capability_ids),
                "render_receipt": render_receipt,
            },
        },
        format="video",
    )
