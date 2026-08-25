# Phase 3 — Narration, contracts, and timeline

**Status:** Implemented.

## Trusted narration

After `VideoPlan` validation, the backend resolves the configured TTS provider, language, and voice using existing podcast/video policy. Provider credentials and network access remain in the backend. All utterances are synthesized concurrently inside one existing `video_presentation_generation` billing boundary.

Each result is written through `SandboxSession.write_file()` as:

```text
<attempt-workdir>/public/utterance-{utterance_id}.{container}
```

Beat and utterance IDs must be unique safe identities; paths must remain below `/workspace`. ffprobe measures every output. Empty audio, invalid media duration, quota/billing failure, incomplete coverage, or a summed narration duration above 180 seconds stops the attempt before the final render.

The job-local public directory is then copied into the prebuilt bundle’s serve root. Narration is temporary attempt data, not a separate Artifact.

## Contract layers

The implementation intentionally has three strict representations:

1. `CreativeOutline`: semantic visual intents used only for retrieval.
2. `VideoPlan`: model-authored declarative content bound to the disclosed capability build.
3. `VideoRenderInput`: backend-compiled, renderer-facing absolute timing and adapted layer props.

Python `VideoRenderInput` mirrors the baked Zod schema. Both require schema version 1, the capability `build_id`, `skill_version`, 1920×1080, 30 fps, at most 5,400 frames, at most 12 beats, at most 11 transitions, confined public paths, and declared capability use.

Core render layers cover text/rich text, shapes/gradients, image/video, SVG/icon, chart, code, connector, audio visualization, repeated elements, and bounded groups. Specialized render layers are limited to the two vetted components; the only specialized transition is the vetted whip-pan adapter.

## Deterministic timeline compilation

`compile_video_timeline()` treats measured audio as authoritative:

- narration frames are `ceil(duration_seconds × 30)`;
- each beat duration is the maximum of narration, authored minimum, and selected capability natural-length floor;
- adjacent beats overlap only by the declared transition duration;
- narration tracks never overlap;
- a transition may not exceed half either adjacent beat;
- layers are converted from beat-relative to absolute intervals and may not exceed their beat;
- safe-margin layers stay 72 px from the 1920×1080 edge;
- total generated elements are capped at 200;
- total duration may not exceed 5,400 frames.

Unspecified beat seeds are SHA-256-derived from build ID, title, and beat ID. Selected IDs and assets are canonically sorted. The render input seed is derived from build ID and title. Identical plan, capability build, skill version, and measured narration therefore compile identically.

`build_video_render_input()` adapts plan layers to the exact renderer schema, maps declared assets, emits absolute beats/transitions/audio tracks, and rejects any unsupported capability adapter.

## Failure and cancellation rules

- Narration failure creates no Artifact and does not enter preflight.
- Capability/build/props/path/timing errors are validation failures, not renderer fallback opportunities.
- The persisted cancellation watcher can cancel in-flight TTS and terminate the attempt sandbox.
- The 180-second product cap is separate from Celery’s soft/hard execution limits.
- Final composition metadata independently rechecks duration, frame count, dimensions, and fps.

## Evidence

`tests/unit/deliverables/video/test_timeline.py` covers deterministic normalization/timeline behavior, measured narration coverage, bounds, transition timing, and render-input construction. `test_video_executor.py` verifies that TTS occurs once after the two-stage plan and before preflight. Narration unit coverage validates provider resolution, path confinement, concurrent synthesis, probing, billing, and duration rejection.
