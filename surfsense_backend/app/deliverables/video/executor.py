"""Queued, capability-aware orchestration for the static video renderer."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from pathlib import PurePosixPath
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.chat.multi_agent_chat.subagents.builtins.deliverables.tools.review_video_stills import (
    review_video_stills,
)
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
from app.deliverables.video.compiler import (
    VideoCompilerError,
    compile_video_plan,
    disclosed_capability_slots,
)
from app.deliverables.video.contracts import (
    AuthoredVideoPlan,
    CreativeOutline,
    NarrationRewrite,
    VideoPlan,
    VideoRenderInput,
)
from app.deliverables.video.narration import (
    NarrationUtterance,
    merge_narration_audio,
    synthesize_narration,
)
from app.deliverables.video.skill import LoadedVideoSkill, load_video_skill
from app.deliverables.video.timeline import (
    VideoTimelineDurationError,
    build_video_render_input,
)
from app.sandbox import SandboxResourceProfile, SandboxSession, get_registry
from app.sandbox.capabilities import (
    CapabilityFilter,
    RetrievalQuery,
    build_capability_disclosure,
    load_capability_index,
    retrieve_capabilities,
    validate_disclosable_capabilities,
)
from app.sandbox.capabilities.retrieval import RetrievedCapability
from app.sandbox.capabilities.schema import (
    CapabilityDisclosure,
    CapabilityIndex,
    CapabilityKind,
)
from app.services.llm_service import get_vision_llm
from app.utils.structured_output import invoke_json

_MAX_BRIEF_CHARS = 16_000
_MAX_SOURCE_REFERENCES = 25
_MAX_SOURCE_REFERENCE_CHARS = 1_000
_MODEL_TIMEOUT_SECONDS = 120
_FINDINGS_CHARS = 16_000
logger = logging.getLogger(__name__)
_ALWAYS_DISCLOSED_CAPABILITY_IDS = (
    "video.renderer.master",
    "video.component.core.primitives",
    "font.inter",
    "font.lora",
    "font.jetbrains-mono",
)


class DeliverableJobCancellationError(Exception):
    """Raised when the persisted lifecycle no longer permits executor work."""


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


class VideoExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: int
    generation: int
    title: str
    output_path: str
    beat_count: int
    duration_seconds: float
    repair_count: Annotated[int, Field(ge=0, le=VIDEO_SPEC.max_repair_cycles)]


def video_sandbox_owner(job_id: int, attempt_count: int) -> str:
    return f"deliverable-job-{job_id}-attempt-{attempt_count}"


async def execute_video_deliverable(
    session: AsyncSession,
    job: DeliverableJob,
    llm,
) -> VideoExecutionResult:
    """Plan, narrate, preflight, render once, verify, and persist one job."""

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
    sandbox = await (await get_registry()).get_session(
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

    await heartbeat("preparing", 5)
    await _stage_runtime(sandbox, workdir)
    skill, index = await asyncio.gather(
        load_video_skill(sandbox),
        load_capability_index(sandbox, image_digest=None),
    )
    _validate_required_capabilities(index)
    validate_disclosable_capabilities(index)

    await heartbeat("outlining", 10)
    outline = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "phase": "creative_outline",
            "title": job.title,
            "brief": request.brief,
            "source_references": _source_labels(request.source_references),
            "revision_artifact_id": request.revision_artifact_id,
            "capability_taxonomy": _capability_taxonomy(index),
            "output_schema": CreativeOutline.model_json_schema(),
        },
        model=CreativeOutline,
    )
    await heartbeat("retrieving", 18)
    disclosure = _retrieve_disclosure(index, outline)

    await heartbeat("planning", 25)
    authored = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "phase": "video_plan",
            "request_title": job.title,
            "brief": request.brief,
            "source_references": _source_labels(request.source_references),
            "outline": outline.model_dump(mode="json"),
            "capability_disclosure": _authored_capability_disclosure(disclosure),
            "output_schema": AuthoredVideoPlan.model_json_schema(),
        },
        model=AuthoredVideoPlan,
    )
    plan = await _compile_with_semantic_repair(
        llm,
        skill=skill,
        authored=authored,
        index=index,
        disclosure=disclosure,
    )

    await heartbeat("narrating", 35)
    narration = await synthesize_narration(
        [
            {
                "beat_id": beat.beat_id,
                "utterance_id": beat.utterance_id,
                "transcript": beat.narration,
            }
            for beat in plan.beats
        ],
        str(workdir),
        workspace_id=job.workspace_id,
        thread_id=request.root_thread_id,
        session=sandbox,
        language=plan.language,
    )
    natural_frames = {
        capability.id: capability.natural_frame_length
        for capability in index.capabilities
        if capability.natural_frame_length is not None
    }
    try:
        render_input = build_video_render_input(
            plan,
            narration,
            skill_version=skill.sha256,
            capability_natural_frames=natural_frames,
        )
    except VideoTimelineDurationError as exc:
        await heartbeat("repairing_narration", 44)
        plan, replacement_requests = await _request_narration_repair(
            llm,
            skill=skill,
            plan=plan,
            duration_error=exc,
        )
        replacements = await synthesize_narration(
            replacement_requests,
            str(workdir),
            workspace_id=job.workspace_id,
            thread_id=request.root_thread_id,
            session=sandbox,
            language=plan.language,
        )
        narration = merge_narration_audio(narration, replacements)
        render_input = build_video_render_input(
            plan,
            narration,
            skill_version=skill.sha256,
            capability_natural_frames=natural_frames,
        )
    await _publish_job_assets(sandbox, workdir)

    vision_llm = await get_vision_llm(
        session, job.workspace_id, usage_type="video_still_review"
    )
    repairs = 0
    while True:
        props_path = await _write_render_input(sandbox, workdir, render_input)
        await heartbeat("reviewing", min(72, 48 + repairs * 12))
        issue = await _preflight_and_review(
            sandbox,
            vision_llm=vision_llm,
            workdir=workdir,
            props_path=props_path,
        )
        if issue is None:
            break
        if repairs >= VIDEO_SPEC.max_repair_cycles:
            raise RuntimeError(f"video preflight/still review failed: {issue}")
        await heartbeat("repairing", min(76, 60 + repairs * 8))
        plan = await _repair_plan(
            llm,
            skill=skill,
            plan=plan,
            findings=issue,
            index=index,
            disclosure=disclosure,
        )
        render_input = build_video_render_input(
            plan,
            narration,
            skill_version=skill.sha256,
            capability_natural_frames=natural_frames,
        )
        repairs += 1

    await heartbeat("rendering", 80)
    await _render(sandbox, workdir, props_path, output_path)
    await heartbeat("verifying", 90)
    verification_llm = await get_vision_llm(
        session, job.workspace_id, usage_type="artifact_verification"
    )
    verification = await verify_artifact(
        sandbox,
        output_path,
        workspace_id=job.workspace_id,
        vision_llm=verification_llm,
    )
    if not verification.verified:
        raise RuntimeError(
            "video verification failed: " + "; ".join(verification.findings)
        )

    await heartbeat("saving", 95)
    saved = await _save_verified(
        session,
        sandbox,
        job=job,
        request=request,
        plan=plan,
        render_input=render_input,
        skill=skill,
        index=index,
        output_path=output_path,
    )
    await _cleanup_attempt(sandbox, workdir, output_path)
    return VideoExecutionResult(
        artifact_id=saved.artifact_id,
        generation=saved.generation,
        title=saved.title,
        output_path=output_path,
        beat_count=len(plan.beats),
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
        f"rm -f -- {quoted}/cancel",
        "stage prebuilt video runtime",
    )


async def _publish_job_assets(sandbox: SandboxSession, workdir: PurePosixPath) -> None:
    """Copy job-authored public files into the prebuilt bundle's serve root."""

    await _run_checked(
        sandbox,
        f"cp -a --reflink=auto {shlex.quote(str(workdir / 'public'))}/. "
        f"{shlex.quote(str(workdir / 'bundle' / 'public'))}/",
        "publish job-local video assets",
    )


def _source_labels(references: list[str]) -> list[dict[str, str]]:
    return [
        {"label": f"Source {index}", "reference": reference}
        for index, reference in enumerate(references, start=1)
    ]


async def _invoke_structured(
    llm,
    *,
    skill: LoadedVideoSkill,
    payload: dict,
    model: type[BaseModel],
):
    return await asyncio.wait_for(
        invoke_json(
            llm,
            [
                SystemMessage(content=skill.content),
                HumanMessage(
                    content=json.dumps(payload, ensure_ascii=False, sort_keys=True)
                ),
            ],
            model,
        ),
        timeout=_MODEL_TIMEOUT_SECONDS,
    )


def _retrieve_disclosure(
    index: CapabilityIndex, outline: CreativeOutline
) -> CapabilityDisclosure:
    by_id = index.by_id()
    retrieved = [
        RetrievedCapability(
            capability=by_id[capability_id],
            score=10**9,
            matched_terms=("required",),
        )
        for capability_id in _ALWAYS_DISCLOSED_CAPABILITY_IDS
    ]
    known_categories = {capability.category for capability in index.capabilities}
    for intent in outline.visual_intents:
        categories = frozenset(set(intent.categories) & known_categories)
        retrieved.extend(
            retrieve_capabilities(
                index,
                RetrievalQuery(
                    text=" ".join(
                        (intent.description, *intent.categories, *intent.tags)
                    ),
                    facets=CapabilityFilter(
                        domains=frozenset({"video"}),
                        kinds=frozenset(
                            {
                                CapabilityKind.FONT,
                                CapabilityKind.COMPONENT,
                                CapabilityKind.TRANSITION,
                            }
                        ),
                        categories=categories,
                        maximum_natural_frames=(
                            round(intent.target_duration_seconds * 30)
                            if intent.target_duration_seconds is not None
                            else None
                        ),
                    ),
                    desired_vibe=intent.vibe,
                    avoid=intent.avoid,
                    top_k=3,
                ),
            )
        )
    return build_capability_disclosure(index.build_id, retrieved)


def _validate_required_capabilities(index: CapabilityIndex) -> None:
    missing = set(_ALWAYS_DISCLOSED_CAPABILITY_IDS) - set(index.by_id())
    if missing:
        raise ValueError(f"live capability index lacks required IDs: {sorted(missing)}")


def _capability_taxonomy(index: CapabilityIndex) -> dict[str, object]:
    """Expose bounded vocabulary; concrete capabilities are retrieved after outlining."""

    visible = tuple(
        capability
        for capability in index.capabilities
        if capability.kind is not CapabilityKind.RENDERER
    )
    return {
        "capability_count": len(visible),
        "kinds": sorted({capability.kind.value for capability in visible}),
        "categories": sorted({capability.category for capability in visible}),
        "vibes": sorted({vibe for capability in visible for vibe in capability.vibe}),
    }


def _authored_capability_disclosure(
    disclosure: CapabilityDisclosure,
) -> dict[str, object]:
    slots = []
    font_ids = []
    for slot, candidate in disclosed_capability_slots(disclosure):
        metadata = {
            "category": candidate.category,
            "summary": candidate.summary,
            "tags": list(candidate.tags),
            "vibe": list(candidate.vibe),
            "use_for": list(candidate.use_for),
            "avoid_for": list(candidate.avoid_for),
            "natural_frame_length": candidate.natural_frame_length,
        }
        slots.append(
            {
                "slot": slot,
                "kind": candidate.kind.value,
                "metadata": metadata,
                "props_schema": candidate.props_schema,
            }
        )
        if candidate.kind is CapabilityKind.FONT:
            font_ids.append(candidate.id)
    return {
        "build_id": disclosure.build_id,
        "capability_slots": slots,
        "font_ids": font_ids,
    }


async def _compile_with_semantic_repair(
    llm,
    *,
    skill: LoadedVideoSkill,
    authored: AuthoredVideoPlan,
    index: CapabilityIndex,
    disclosure: CapabilityDisclosure,
) -> VideoPlan:
    try:
        return compile_video_plan(authored, index=index, disclosure=disclosure)
    except VideoCompilerError as exc:
        if VIDEO_SPEC.max_repair_cycles < 1:
            raise
        repaired = await _invoke_structured(
            llm,
            skill=skill,
            payload={
                "phase": "semantic_compile_repair",
                "diagnostics": [
                    diagnostic.model_dump(mode="json") for diagnostic in exc.diagnostics
                ],
                "authored_video_plan": authored.model_dump(mode="json"),
                "capability_disclosure": _authored_capability_disclosure(disclosure),
                "output_schema": AuthoredVideoPlan.model_json_schema(),
            },
            model=AuthoredVideoPlan,
        )
        return compile_video_plan(repaired, index=index, disclosure=disclosure)


async def _request_narration_repair(
    llm,
    *,
    skill: LoadedVideoSkill,
    plan: VideoPlan,
    duration_error: VideoTimelineDurationError,
) -> tuple[VideoPlan, list[NarrationUtterance]]:
    budgets = {
        budget.beat_id: budget for budget in duration_error.suggested_narration_budgets
    }
    rewrite = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "phase": "narration_duration_repair",
            "diagnostics": {
                "max_frames": duration_error.max_frames,
                "compiled_frames": duration_error.compiled_frames,
                "overflow_frames": duration_error.overflow_frames,
            },
            "budgets": [
                {
                    "beat_id": budget.beat_id,
                    "max_seconds": budget.max_seconds,
                    "max_words": budget.max_words,
                }
                for budget in duration_error.suggested_narration_budgets
            ],
            "narration": [
                {
                    "beat_id": beat.beat_id,
                    "utterance_id": beat.utterance_id,
                    "narration": beat.narration,
                }
                for beat in plan.beats
            ],
            "instructions": (
                "Rewrite only narration that cannot fit its budget. Preserve beat_id "
                "and utterance_id exactly. Do not return visual or timing fields."
            ),
            "output_schema": NarrationRewrite.model_json_schema(),
        },
        model=NarrationRewrite,
    )
    original_by_beat = {beat.beat_id: beat for beat in plan.beats}
    rewritten_text: dict[str, str] = {}
    replacement_requests: list[NarrationUtterance] = []
    for item in rewrite.beats:
        original = original_by_beat.get(item.beat_id)
        if original is None or original.utterance_id != item.utterance_id:
            raise ValueError(
                "narration repair changed protected beat or utterance identity"
            )
        budget = budgets[item.beat_id]
        if len(item.narration.split()) > budget.max_words:
            raise ValueError(
                f"narration repair for {item.beat_id!r} exceeds its "
                f"{budget.max_words}-word budget"
            )
        if item.narration == original.narration:
            continue
        rewritten_text[item.beat_id] = item.narration
        replacement_requests.append(
            NarrationUtterance(
                beat_id=item.beat_id,
                utterance_id=item.utterance_id,
                transcript=item.narration,
                max_words=budget.max_words,
            )
        )
    if not replacement_requests:
        raise ValueError("narration repair did not change any utterance")
    repaired = plan.model_copy(
        update={
            "beats": tuple(
                beat.model_copy(
                    update={
                        "narration": rewritten_text.get(beat.beat_id, beat.narration)
                    }
                )
                for beat in plan.beats
            )
        }
    )
    return repaired, replacement_requests


async def _repair_plan(
    llm,
    *,
    skill: LoadedVideoSkill,
    plan: VideoPlan,
    findings: str,
    index: CapabilityIndex,
    disclosure: CapabilityDisclosure,
) -> VideoPlan:
    authored = await _invoke_structured(
        llm,
        skill=skill,
        payload={
            "phase": "visual_repair",
            "findings": findings[:_FINDINGS_CHARS],
            "preserve": ["beat_ids", "utterance_ids", "narration", "language"],
            "capability_disclosure": _authored_capability_disclosure(disclosure),
            "current_internal_video_plan": plan.model_dump(mode="json"),
            "output_schema": AuthoredVideoPlan.model_json_schema(),
        },
        model=AuthoredVideoPlan,
    )
    repaired = compile_video_plan(authored, index=index, disclosure=disclosure)
    before = [(beat.beat_id, beat.utterance_id, beat.narration) for beat in plan.beats]
    after = [
        (beat.beat_id, beat.utterance_id, beat.narration) for beat in repaired.beats
    ]
    if repaired.language != plan.language or after != before:
        raise ValueError(
            "visual repair changed protected narration identity or language"
        )
    return repaired


async def _write_render_input(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    render_input: VideoRenderInput,
) -> str:
    path = str(workdir / "props.json")
    await sandbox.write_file(
        path,
        (
            render_input.model_dump_json(by_alias=True, exclude_none=True) + "\n"
        ).encode(),
    )
    return path


async def _preflight_and_review(
    sandbox: SandboxSession,
    *,
    vision_llm,
    workdir: PurePosixPath,
    props_path: str,
) -> str | None:
    result = await _run_bash(
        sandbox,
        _render_command(workdir, "--preflight", props_path),
    )
    if not result.ok:
        return result.output[-_FINDINGS_CHARS:]

    stills_dir = workdir / "stills"
    result = await _run_bash(
        sandbox,
        _render_command(workdir, "--stills", props_path, stills_dir),
    )
    if not result.ok:
        return result.output[-_FINDINGS_CHARS:]
    stills = await _discover_stills(sandbox, workdir, stills_dir)
    review = await review_video_stills(
        stills,
        session=sandbox,
        vision_llm=vision_llm,
        workdir=workdir,
    )
    if review["status"] != "reviewed":
        return None
    blocking = [
        f"{criterion}: {'; '.join(value['evidence']) or 'blocking finding'}"
        for criterion, value in review["review"].items()
        if isinstance(value, dict) and value.get("verdict") == "blocking"
    ]
    return "; ".join(blocking) or None


async def _discover_stills(
    sandbox: SandboxSession,
    workdir: PurePosixPath,
    stills_dir: PurePosixPath,
) -> list[str]:
    script = (
        "import glob,json,os,sys;"
        "root=sys.argv[1];base=sys.argv[2];"
        "print(json.dumps([os.path.relpath(p,root) for p in "
        "sorted(glob.glob(os.path.join(base,'*.png')))]))"
    )
    result = await sandbox.run_command(
        f"python3 -c {shlex.quote(script)} "
        f"{shlex.quote(str(workdir))} {shlex.quote(str(stills_dir))}"
    )
    if not result.ok:
        raise RuntimeError(f"Could not discover risk stills: {result.output[-4000:]}")
    try:
        paths = json.loads(result.output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Risk still discovery returned invalid JSON") from exc
    if (
        not isinstance(paths, list)
        or not paths
        or "stills/contact-sheet.png" not in paths
        or any(not isinstance(path, str) for path in paths)
    ):
        raise RuntimeError("Risk still output is incomplete")
    return paths


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
    *arguments: str | PurePosixPath,
) -> str:
    quoted_arguments = " ".join(shlex.quote(str(argument)) for argument in arguments)
    return (
        f"cd -- {shlex.quote(str(workdir))} && "
        f"VIDEO_SANDBOX_FRAME_CONCURRENCY="
        f"{app_config.VIDEO_SANDBOX_FRAME_CONCURRENCY} node render.mjs "
        f"--bundle-dir {shlex.quote(str(workdir / 'bundle'))} {quoted_arguments}"
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
    """Best-effort removal after the verified MP4 is durably persisted."""

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


def _markdown(plan: VideoPlan) -> str:
    sections = [
        f"## {beat.beat_id}\n\n**Narration:** {beat.narration}" for beat in plan.beats
    ]
    return f"# {plan.title}\n\n" + "\n\n".join(sections)


async def _save_verified(
    session: AsyncSession,
    sandbox: SandboxSession,
    *,
    job: DeliverableJob,
    request: VideoJobRequestV1,
    plan: VideoPlan,
    render_input: VideoRenderInput,
    skill: LoadedVideoSkill,
    index: CapabilityIndex,
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
    if (
        render_receipt.get("build_id") != index.build_id
        or render_receipt.get("skill_version") != skill.sha256
        or render_receipt.get("expected_frame_count") != render_input.duration_in_frames
    ):
        raise ValueError("video render receipt does not match the final render input")

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
        markdown_representation=_markdown(plan),
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
                "skill_version": skill.sha256,
                "skill_files": list(skill.files),
                "selected_capability_ids": list(render_input.selected_capability_ids),
                "render_receipt": render_receipt,
            },
        },
        format="video",
    )
