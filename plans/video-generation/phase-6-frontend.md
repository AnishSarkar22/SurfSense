# Phase 6 — Unchanged frontend delivery

**Status:** Implemented. The capability-aware renderer did not introduce a new frontend media architecture.

## Pending lifecycle

When the feature flag selects the new path, the enqueue receipt supplies a stable `job_id` and title. The existing deliverable-job card subscribes to the safe Zero projection and renders:

```text
queued      → generating + Cancel
running     → safe phase label + Cancel
cancelling  → cancelling
cancelled   → cancelled + Retry
failed      → mapped safe failure + Retry
ready       → existing MP4 Artifact card
```

The database/Zero state is authoritative. Cancel and Retry use the existing workspace/job routes; controls disable while requests are pending and do not invent optimistic terminal states. The card intentionally displays neither infrastructure details nor a percentage.

Published fields remain ID, kind, title, status, phase, progress, stable failure code, nullable Artifact ID, workspace/thread attribution, and timestamps. Request data, capability disclosure, model output, task identity, attempts, internal error, sandbox details, billing, render metadata, and credentials remain private.

## Ready handoff

`ready` with an Artifact ID renders the existing `Mp4ArtifactCard`. That component:

1. loads the generic Artifact manifest;
2. selects the PRIMARY `video/mp4` file;
3. passes its authenticated content URL to the shared Video.js player;
4. preserves inline playback and `preload="none"`;
5. uses the existing Range-backed seek and download behavior.

Ready without an Artifact ID shows the existing unavailable state. No capability metadata is required to play the final MP4, and the browser does not load the authoring skill, catalog, renderer bundle, or render input.

## Other surfaces

The Artifact library merges queued/running/cancelling video jobs while ready output comes from the normal Artifact list. Pending job receipts are not placeholder Artifacts. Existing knowledge-base MP4 viewing uses the same manifest/player path.

The flag-off `VideoPresentationRun` UI remains a separate supported path through
the Phase 7 rollout window. Phase 8 removes it only after production acceptance;
see [legacy-boundary.md](legacy-boundary.md).

## Evidence

Frontend tests cover enqueue bootstrap, Zero loading/missing states, all lifecycle states, safe fallback copy, fixed card layout, absence of a visible progress percentage, exact Cancel/Retry routes, web/desktop request routing, disabled pending actions, ready handoff, lazy Video.js loading, and direct media-source playback.
