# Phase 4 — Preflight, review, render, and verification

**Status:** Implemented.

## Pre-render gates

Every candidate `VideoRenderInput` runs through the same static bundle:

1. Zod validation and capability schema/build checks.
2. `selectComposition()` with exact 1920×1080, 30 fps, frame count, and duration checks.
3. Risk-still rendering at frame 0, final frame, beat midpoints, and authored keyframes.
4. ffmpeg contact-sheet creation.
5. Optional vision review for clipping, overflow, hierarchy, contrast, blank output, and safe margins.

Native preflight and still generation are mandatory. If no vision model is available, visual review is recorded as unavailable and does not replace the structural gates. Blocking findings can trigger a bounded declarative repair followed by a fresh preflight/still pass.

## Single full render

After review passes, `render.mjs` acquires an admission slot and calls `renderMedia()` exactly once. It renders H.264/AAC/yuv420p with an enforced audio track to a temporary `.mp4`, handles cancellation, atomically renames successful output, and writes `<output>.render.json`.

The render metadata binds:

- schema, capability build, and skill versions;
- SHA-256 of the exact render input;
- expected duration and frame count;
- all risk-sample frames and reasons;
- sorted selected and resolved capability IDs and counts;
- codec, audio codec, pixel format, dimensions, and fps;
- measured render seconds and completion timestamp.

Selected and resolved IDs must be equal. A render or final verification failure is terminal for that attempt; the executor does not perform a second full render.

## Artifact verification

The video adapter runs in the sandbox and requires:

- valid render metadata matching the live capability index/build;
- exactly one 1920×1080 H.264 video stream;
- exactly one non-empty AAC narration stream;
- positive duration within 0.5 seconds of render metadata;
- frame count equal to expected frames;
- narration that does not end more than 0.5 seconds before video;
- every recorded risk frame to have sufficient grayscale levels and variance;
- a valid SHA-256 of the exact MP4.

Only compact findings and the digest cross the sandbox boundary. Generic verification may also use the configured vision model. The verification service signs a receipt bound to workspace, canonical format `video`, exact output path, and primary SHA-256.

## Persistence gate and failures

Before save, the executor rereads the signed receipt and render metadata. Format/path, capability build, skill hash, and frame count must match the final input. Storage recomputes SHA-256 while streaming and rejects changed bytes.

Failures map at the worker boundary:

- policy duration errors → `duration_limit`;
- render/browser/ffmpeg/time-limit errors → `render_failed`;
- verification or receipt errors → `verification_failed`;
- quota errors → `quota_exceeded`;
- remaining author/provider errors → `generation_failed`.

Internal diagnostics are bounded, credential-like values are redacted, and public state receives only the stable code.

## Evidence

- `harness-tests/capabilities.test.mjs` asserts the sole `renderMedia()` call and complete sidecar fields.
- `tests/unit/artifacts/test_video_verification.py` covers metadata/index agreement, stream/frame/audio requirements, sampled-frame checks, and digest production.
- `tests/unit/artifacts/test_video_verification_ffmpeg.py` exercises ffmpeg/ffprobe command behavior.
- executor tests verify that save follows successful verification and exact receipt matching.

These are correctness checks, not published performance measurements.
