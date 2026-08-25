# Capability-aware video artifacts — as built

**Status:** Implemented. This directory documents the running architecture, not a roadmap.

## System shape

```text
video request
  → feature-gated interactive routing
  → idempotent DeliverableJob
  → deliverables.execute_queued on the shared Celery worker
  → attempt-owned network-disabled sandbox
  → load baked skill + baked capability index
  → outline → retrieve/disclose → declarative VideoPlan
  → trusted TTS → measured timeline → VideoRenderInput
  → preflight → risk stills/contact sheet → optional visual repair
  → one renderMedia() call → structural/visual verification
  → receipt-bound streaming Artifact save → DeliverableJob.ready
  → existing MP4 manifest, Range, player, and download path
```

The database is lifecycle authority; Celery transports and executes work. Each retry has a distinct task identity, sandbox owner, work directory, and output path. The renderer executes only the static, image-baked `MasterComposition` against strict declarative data.

## Runtime capability set

The generated index currently contains exactly eight stable IDs:

1. `font.inter`
2. `font.jetbrains-mono`
3. `font.lora`
4. `video.component.core.primitives`
5. `video.renderer.master`
6. `video.component.animated-bar-chart`
7. `video.component.blur-out-up`
8. `video.transition.whip-pan`

This is a curated runtime, not a copy of any live upstream catalog. Only vetted, offline, deterministic, composable atoms with explicit adapters, bounded props, and deterministic fixtures enter the image. Two vendored components and one vendored transition are installed today.

Capability IDs are semantic and stable. `build_id` is the first 20 hex characters of a SHA-256 over the sorted indexed declarations; any indexed contract change produces a new build. Plans, render inputs, renderer registry, render metadata, verifier, and saved artifact metadata carry that build ID and fail closed on mismatch.

## Trust boundaries and invariants

- The sandbox image supplies the skill, supplements, capability metadata, adapters, fonts, bundle, browser, and ffmpeg.
- The model first authors a compact outline from aggregate kinds, categories, and vibes; the outline prompt does not grow with the catalog. Backend retrieval uses build-generated weighted postings and discloses up to three matches per visual intent plus required core facilities, within a 48-candidate/128 KiB global bound. A second model call may select only disclosed IDs and admitted props.
- The backend assigns the capability build, validates exact selected-versus-used capability equality, and compiles timing from measured narration.
- The runtime is fixed at 1920×1080, 30 fps, at most 12 beats, and at most 5,400 frames/180 seconds.
- Visual repairs are declarative and may not change beat IDs, utterance IDs, narration, or language. At most two pre-render repairs are allowed.
- Preflight and still review finish before the sole full render. A failed final render or verification fails the attempt; it does not start another full render.
- Only bytes covered by the signed verification receipt can be persisted.
- Public state exposes stable lifecycle/failure fields, not provider, sandbox, browser, ffmpeg, path, credential, or stack details.

## Supply chain

`docker/sandbox/video-runtime/scripts/build-capabilities.mjs` validates source declarations and JSON Schemas, resolves co-located component/transition adapters by convention, rejects excluded timeline-owning entries, sorts IDs, generates the searchable index and static TypeScript registries, transpiles the render-input schema, and copies the declared fonts. Loader names and module paths are build-only and are removed from the runtime index. Local output stays under the ignored `video-runtime/generated` directory; image builds write the authoritative index directly to `/opt/surfsense/capabilities/index.json`. `npm run build` then creates the static bundle. The Docker build runs type checks and capability tests before pruning development dependencies.

Capability implementations, declarations, provenance, policy, and attribution live together under `docker/sandbox/video-runtime/src/capabilities`. Refreshing the catalog is an explicit review operation:

1. inspect upstream catalog/docs and license;
2. choose an atom that satisfies the offline/deterministic/composable policy;
3. vendor and review its implementation rather than importing a live registry at runtime;
4. add a bounded declaration beside its convention-named adapter, deterministic fixture, provenance revision, and attribution;
5. run `npm run generate`, `npm run check`, `npm test`, and `npm run build`;
6. review the changed index/build ID and run the render smoke/benchmark in the built sandbox.

No refresh step bulk-vendors the upstream catalog.

## Operations

The video-specific operator environment is exactly:

```text
VIDEO_SANDBOX_RENDERING_ENABLED=FALSE
VIDEO_SANDBOX_MAX_CONCURRENT_RENDERS=1
VIDEO_SANDBOX_RENDER_FRAME_TIMEOUT_MS=7000
```

The feature also requires the existing sandbox configuration and TTS/provider configuration. The frame timeout must be at least 7000 ms; concurrency must be a positive integer. There is no additional video frame-chunk setting.

The benchmark interface is:

```bash
cd docker/sandbox/video-runtime
npm run benchmark -- 30 60 180
```

Arguments are any subset of `30`, `60`, and `180`; omission runs all three. Each fixture emits one JSON record containing fixture/frame count, build ID, catalog-load time, preflight/stills/render wall time and maximum RSS, output bytes, and renderer-receipt render time. No measured timing is asserted in this documentation.

The host completed a one-second preflight and single-pass render after installing the rendering browser. Full still/contact-sheet smoke and 30/60/180 benchmarks remain blocked locally by the unavailable Docker daemon and missing host ffmpeg. The production Dockerfile installs both Chrome Headless Shell and ffmpeg, so image-based smoke and benchmark runs remain the authoritative release gate.

## Phase map

- [Phase 1](phase-1-sandbox-harness.md): capability build supply chain and static renderer.
- [Phase 2](phase-2-video-skill.md): skill separation, retrieval, authoring, jobs, and routing.
- [Phase 3](phase-3-narration-bridge.md): narration, contracts, and deterministic timeline compilation.
- [Phase 4](phase-4-verification.md): preflight, still review, render metadata, and verification.
- [Phase 5](phase-5-persistence-and-serving.md): persistence, storage, and Range playback.
- [Phase 6](phase-6-frontend.md): unchanged frontend delivery contract.
- [Legacy boundary](legacy-boundary.md): the two separate systems during rollout.
- [Phase 7](phase-7-migration-backfill.md): production rollout and server-side backfill of stored scene videos into verified MP4 Artifacts.
- [Phase 8](phase-8-retire-legacy.md): direct removal of the flag-off system after production acceptance.
