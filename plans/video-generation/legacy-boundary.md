# Legacy boundary — two separate video systems

**Status:** Current production boundary. The flag-off path remains supported
during rollout and backfill, then is retired after the Phase 7 gates pass.

## Routing rule

`VIDEO_SANDBOX_RENDERING_ENABLED` selects the system used for a new video request:

- `false`: the existing `generate_video_presentation` tool, video-presentation agent/task, and `VideoPresentationRun` lifecycle remain in use.
- `true` with sandboxing enabled: the interactive tool creates a `DeliverableJob`, and the shared Celery worker runs the capability-aware declarative executor.

When sandboxing is unavailable, tool loading retains the existing video-presentation path. The capability-aware executor also checks the flag and refuses to start when disabled.

## No live runtime bridge

The two lifecycles are separate:

```text
legacy: VideoPresentationRun
new:    DeliverableJob → verified MP4 Artifact
```

New requests never cross between these lifecycles. Enabling the flag affects new
routing only; disabling it does not convert or cancel an existing
`DeliverableJob`.

The new renderer accepts only strict declarative `VideoPlan`/`VideoRenderInput`
data bound to its baked capability build. It cannot consume historical scene
payloads.

Phase 7 is a separate, temporary migration operation: it executes stored scene
source in a network-disabled sandbox and saves the result as a verified MP4 on
the same Artifact. It does not translate legacy source into the new plan schema,
and its migration adapter is never used for newly authored videos.

## Operational consequence

- Do not point one lifecycle’s APIs, Zero rows, retry/cancel actions, or persistence assumptions at the other.
- Backfilled content becomes an MP4 Artifact; it does not become a
  capability-authored video.
- Do not remove the flag-off path before the Phase 7 rollout and rollback window completes.
- Phase 8 removes both the legacy runtime and the temporary migration adapter.

See [Phase 7](phase-7-migration-backfill.md) and
[Phase 8](phase-8-retire-legacy.md).
