# Phase 8 — Retire the flag-off legacy system

**Status:** Future work after Phase 7 exit criteria are met.

## Goal

Remove the separate `VideoPresentationRun` implementation after the
capability-aware artifact path is proven in production and Phase 7 has converted
the existing scene-based population to verified MP4 Artifacts.

## Removal scope

- Remove the `generate_video_presentation` interactive tool and legacy routing.
- Remove the video-presentation agent graph, state, prompts, and Celery task.
- Remove legacy-only `VideoPresentationRun` APIs, Zero projections, UI state,
  retry/cancel behavior, and tests.
- Remove `VIDEO_SANDBOX_RENDERING_ENABLED`; the capability-aware
  `DeliverableJob` path becomes unconditional when sandboxing is available.
- Audit and remove `VIDEO_PRESENTATION_*` settings only when no remaining
  podcast, TTS, billing, or shared caller uses them.
- Remove legacy-only dependencies and dead database code.
- Remove the Phase 7 migration adapter, inventory script, and migration-only
  sandbox runtime after the rollback window closes.
- Remove browser scene execution after every historical video has a verified
  MP4 PRIMARY.
- Preserve the generic Artifact MP4 storage, manifest, download, and byte-range
  playback paths used by the new system.

## Data decision

Phase 7 preserves Artifact identity while adding a verified MP4 generation.
Before deleting database readers or tables, choose and document one retention
policy for the obsolete scene source and `VideoPresentationRun` rows:

- retain historical rows read-only for a defined period;
- export required audit metadata and then drop the rows; or
- delete them under the product's approved retention policy.

Do not convert legacy generation payloads into the new declarative schema.
Historical scene videos are re-rendered only by the bounded Phase 7 migration
path, never by the new authoring executor.

## Execution order

1. Confirm Phase 7 approval and close the rollback window.
2. Disable creation of new legacy runs permanently.
3. Verify all historical video playback resolves to a verified MP4 PRIMARY.
4. Apply the approved historical-data retention decision.
5. Delete legacy backend, worker, browser renderer, migration adapter,
   configuration, and tests.
6. Remove the feature flag and simplify routing to the new executor.
7. Run the complete deliverable, artifact, storage, playback, billing, and
   frontend suites.
8. Deploy and confirm no production caller references the removed lifecycle.

## Exit criteria

- New video requests have exactly one implementation path.
- No runtime import, route, task, setting, UI, or test references
  `VideoPresentationRun`.
- Historical data follows the approved retention policy.
- Capability-aware video generation and existing MP4 playback remain healthy.
- No adapter, migration layer, or permanent dual-system code remains.
