# Phase 1 — Capability supply chain and static renderer

**Status:** Implemented.

## Image-owned runtime

`docker/sandbox/Dockerfile` extends the existing code-interpreter image with pinned video-engine and React packages, Chrome Headless Shell, ffmpeg/ffprobe, `/opt/surfsense/video-runtime`, `/opt/surfsense/capabilities/index.json`, the video skill, and three local fonts. The renderer needs no network access and accepts no executable author output.

The Docker build runs:

```text
npm ci
npx remotion browser ensure
npm run check
npm test
npm run build
npm prune --omit=dev
```

The resulting bundle is static at `/opt/surfsense/video-runtime/bundle`. An attempt copies the baked runtime to its own work directory and stages only job-local public assets and `props.json`.

## Capability build

Implementations, source declarations, provenance policy, and attribution live together under `video-runtime/src/capabilities`. `scripts/build-capabilities.mjs`:

- accepts only `font`, `component`, `transition`, and `renderer`;
- requires deterministic declarations and unique stable IDs;
- resolves only convention-named, co-located component and transition adapters;
- validates every declared props schema and deterministic fixture at image build time;
- rejects the explicitly excluded timeline-owning entries;
- produces a sorted index and field-weighted inverted postings;
- derives a content-addressed 20-character `build_id`;
- generates lazy loader maps and the trusted-ID registry;
- generates the JavaScript render-input validator;
- copies Inter, Lora, and JetBrains Mono into the served assets.

Today the index has eight entries: three fonts, core primitives, the master renderer, two vendored components, and one vendored transition. It is intentionally smaller than the upstream catalog.

## Vetting and refresh

A catalog refresh is manual and curated. Review upstream behavior and licensing, reject timeline owners/network dependencies/non-deterministic or incompatible atoms, then vendor the chosen source with a convention-named adapter, JSON Schema, deterministic test props, and provenance. Registry wiring, font loading, native-canvas scaling, and agent-hidden module resolution are generated. Run:

```bash
cd docker/sandbox/video-runtime
npm run generate
npm run check
npm test
npm run build
```

Review the generated index and changed build ID. A stable ID must retain its meaning; an incompatible API should receive a new ID. `vendored_revision` records upstream provenance but is not the runtime compatibility key.

## Render interface

`render.mjs` exposes:

```text
node render.mjs --preflight props.json
node render.mjs --stills props.json outdir
node render.mjs props.json out.mp4
```

All modes validate `VideoRenderInput`, index schema/build identity, selected capability membership, composition metadata, 1920×1080 dimensions, 30 fps, and the 180-second ceiling.

`MasterComposition` loads all three fonts, lazily loads selected vetted components, rejects unknown IDs, renders typed core layers and adapted atoms, sequences narration/captions, applies the vetted transition, and adds the watermark. A render-input build mismatch is fatal.

Stills cover timeline boundaries, beat midpoints, and authored keyframes, then ffmpeg creates a contact sheet. Final rendering uses one `renderMedia()` call with H.264, AAC, `yuv420p`, enforced audio, cancellation support, atomic final rename, and a complete `.render.json` sidecar.

## Runtime controls and failures

- `VIDEO_SANDBOX_MAX_CONCURRENT_RENDERS` provides process-host admission slots.
- `VIDEO_SANDBOX_RENDER_FRAME_TIMEOUT_MS` is passed to still and media rendering and must be at least 7000.
- `progress.json` is atomically updated; a cancel marker and SIGINT/SIGTERM trigger renderer cancellation.
- Invalid props, unknown IDs, schema/build drift, missing bundle/browser, metadata mismatch, timeout, cancellation, or render failure stop the attempt.
- Partial media is removed and never promoted to the final output path.

## Evidence

`harness-tests/capabilities.test.mjs` checks index/registry lockstep, excluded entries, trusted declarative input, capability closure, risk-frame selection, font/lazy-loader readiness, deterministic 720p staging, single-pass rendering, and receipt fields. Python capability tests independently parse the generated index with the backend contract.

A host-side one-second preflight and single-pass render passed after installing the rendering browser. Full still/contact-sheet smoke and duration benchmarks require the built image here because the host has no ffmpeg and its Docker daemon is unavailable. The Dockerfile installs the browser, ffmpeg, and `time` expected by those checks.
