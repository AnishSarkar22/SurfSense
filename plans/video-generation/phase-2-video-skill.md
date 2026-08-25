# Phase 2 — Skill, retrieval, authoring, and job routing

**Status:** Implemented.

## Separation of concerns

The sandbox-baked video skill defines creative and review judgment. Backend code defines identity, trust, lifecycle, retrieval bounds, timing, rendering, verification, and persistence. The model authors declarative beats and layers only; it cannot choose commands, files, runtime modules, or lifecycle state.

`load_video_skill()` reads `/opt/skills/video/SKILL.md` from the same live sandbox as the renderer. Frontmatter contains a closed six-file supplement allowlist. Paths are confined below the skill root, the set is bounded, aggregate content is capped at 96 KiB, and the combined content SHA-256 becomes `skill_version` in render and artifact metadata.

## Two-stage authoring

The worker makes two structured model calls before narration:

1. **Creative outline.** Given the request, references, skill, and compact live taxonomy, produce objective, audience, language, and up to 12 visual intents.
2. **Video plan.** Backend lexical retrieval evaluates each intent, creates one bounded disclosure, and supplies exact candidate metadata/props schemas. The model then produces a strict `VideoPlan` using only those candidates.

The disclosure always starts with:

```text
video.renderer.master
video.component.core.primitives
font.inter
font.lora
font.jetbrains-mono
```

Intent retrieval adds ranked fonts/components/transitions. The image build emits separate postings for tags, `use_for`, summary, vibe, category, `avoid_for`, and the combined searchable text, so the worker scores matching postings rather than scanning and tokenizing every capability. Ranking remains deterministic and diversity-aware. Each intent contributes at most three candidates; the combined disclosure is capped at 48 unique candidates and 128 KiB. The final validator rejects non-disclosed IDs, build mismatch, duplicate selection, missing renderer, selected-but-unused IDs, and used-but-unselected IDs.

The model never sees implementation paths or an unbounded catalog. Core primitives remain the fallback when no specialist is a strong semantic fit.

Capability layers and transitions remain generic in both the Python and TypeScript render contracts. Their props are validated against the exact sandbox-provided JSON Schema before narration and again at renderer preflight. Adding a vetted capability therefore does not require another Pydantic/Zod union branch or composition dispatch branch.

## Retrieval fixtures

Backend unit tests use a deliberately synthetic four-entry index:

- `video.component.metric-grid`
- `video.component.metric-cards`
- `video.component.confetti`
- `video.component.core.text`

For “serious quarterly KPI metric comparison,” the fixture asserts deterministic `metric-grid` ranking, exclusion of confetti through avoid terms, diversity, and retention of a core fallback. These names are retrieval-test fixtures only and are not installed runtime capabilities.

A separate 200-entry fixture executes 500 repeated intent searches under a 500 ms test budget. It guards the indexed lookup path and leaves enough margin for shared CI hosts.

## Plan contract and repair

`VideoPlan` fixes schema/build identity, title/language, selected IDs, style, confined assets, and 1–12 uniquely identified beats. Every beat has one stable utterance ID, complete-sentence narration, bounded declarative layers, optional vetted transition, minimum duration, and deterministic seed.

Capability props pass strict per-atom Pydantic models. Text/media/capability references are closed over selected capabilities and declared assets. Bounds, safe margins, generated-element count, paths, durations, and transition placement are validated before rendering.

Preflight or blocking still findings may request a declarative visual repair. A repair receives the same disclosure and must preserve language plus every beat ID, utterance ID, and narration string. `VIDEO_SPEC.max_repair_cycles` is two across the pre-render review loop. Once review passes, the worker performs one full render.

## Durable routing

With both sandboxing and `VIDEO_SANDBOX_RENDERING_ENABLED=true`, the interactive deliverables agent exposes `enqueue_deliverable_job` for video creation, commits an idempotent `DeliverableJob`, dispatches `deliverables.execute_queued`, and returns the pending receipt immediately.

Unique `(workspace_id, kind, tool_call_id)` prevents duplicate jobs. The shared `surfsense` Celery worker claims an attempt atomically and runs `execute_video_deliverable()`. There is no video-specific queue or worker. Policy is 180 seconds, 12 beats, two visual repairs, a 3,600-second soft task limit, and a 3,900-second hard limit.

Attempt identity is:

```text
task:    deliverable-job:{job_id}:attempt:{attempt_count}
owner:   deliverable-job-{job_id}-attempt-{attempt_count}
workdir: /workspace/deliverable-job-{job_id}-attempt-{attempt_count}
output:  /workspace/deliverable-job-{job_id}-attempt-{attempt_count}.mp4
```

Cancellation is database-driven and terminates the exact attempt sandbox. Explicit Retry increments the attempt. Stable public failures are `duration_limit`, `quota_exceeded`, `generation_failed`, `render_failed`, `verification_failed`, and `cancelled`; only classified transient provider errors receive bounded Celery retry.

Flag-off routing is a separate legacy system, documented in [legacy-boundary.md](legacy-boundary.md).

## Evidence

Coverage verifies strict source-free model contracts, exact disclosure closure, narration-preserving repair, ordered outline/retrieval/plan/TTS/review/render/verify/save phases, one TTS pass, two initial model calls, attempt ownership, cancellation heartbeats, revision generation checks, idempotent enqueue, task claims, retry, reconciliation, and sanitized failure mapping.
