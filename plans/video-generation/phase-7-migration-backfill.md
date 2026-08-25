# Phase 7 — Legacy video migration and backfill

**Status:** Future work after Phases 1–6 are deployed and production-validated.

## Goal

Convert every production video Artifact that still stores narration plus
browser-rendered scene source into a verified MP4 PRIMARY file on the same
Artifact. After backfill, playback streams the MP4 and never executes stored
scene code in the client.

This is a one-time server-side sandbox re-render, not a transcode and not part of
the new authoring architecture. The current scene source is the only source from
which those historical videos can be reproduced, so a temporary, versioned
migration adapter is required until the population is converted. Phase 8 removes
that adapter with the rest of the legacy system.

## Preconditions

- Deploy and production-validate the capability-aware `DeliverableJob` path.
- Keep `VIDEO_SANDBOX_RENDERING_ENABLED=false` available as rollback while the
  new path is being validated.
- Reconcile the Artifact-save/job-ready transaction gap before bulk migration.
- Inventory the historical scene schema versions, injected globals, narration
  assets, Artifact identities, and current PRIMARY files.

## Locked migration contract

The implementation must:

1. inventory every legacy video Artifact and classify its source data;
2. create a verified MP4 generation on the same Artifact identity;
3. execute historical scene code only inside a network-disabled sandbox;
4. support known historical globals through a bounded, versioned migration
   runtime without regex source mutation;
5. leave the current PRIMARY untouched until its replacement passes structural
   verification and storage digest validation;
6. preserve original scene and narration inputs through retry and rollback;
7. use the durable `DeliverableJob` lifecycle, generic Celery task, sandbox
   ownership, cancellation, retry, and artifact storage;
8. record an idempotent terminal outcome for every source Artifact; and
9. block Phase 8 while any production video still needs client-side scene
   execution.

The live `VideoPlan` authoring pipeline must not rewrite historical content.
Backfill uses the stored source and a private migration intent, not an LLM.

## Control plane

Add a separately named operator script with dry-run and apply modes:

- dry-run classifies `already-mp4`, `ready`, and `blocked` candidates without
  writes;
- apply creates at most one versioned migration job per source Artifact;
- bounded batches dispatch the existing generic
  `deliverables.execute_queued` task;
- enumeration is resumable and safe against duplicate publication;
- reports expose Artifact ID, source version, outcome, timestamp, and stable
  failure code without leaking source code.

No public backfill API, second lifecycle table, or second Celery task is needed.
The private request schema may carry a versioned backfill intent and source
Artifact ID. Migration-only code must stay outside the normal new-video
executor path.

## Deterministic execution

For each claimed migration job:

1. recheck the Artifact and current PRIMARY to close enumeration races;
2. create an attempt-owned sandbox and network-disabled workdir;
3. stream stored narration and required assets into the workdir;
4. adapt the stored scene source with the matching trusted migration runtime;
5. run preflight and representative still checks;
6. render one H.264/AAC MP4;
7. run structural verification and SHA-256 validation;
8. stream the verified MP4 through generic Artifact storage;
9. atomically make the new generation PRIMARY, then mark the migration outcome;
10. retain original inputs through the accepted rollback window.

A failed or cancelled attempt must leave the original PRIMARY unchanged.

## Outcomes and remediation

- **Backfilled:** a verified MP4 became the Artifact's PRIMARY generation.
- **Already migrated:** a valid MP4 PRIMARY already existed.
- **Blocked:** source data is missing or migration render/verification failed.

`Blocked` is not an acceptable Phase 7 endpoint. Operators must restore inputs,
fix the bounded migration runtime, or approve another server-side export path.
Continuing to execute scene code in the browser is not remediation.

## Production operation

- Start with representative artifacts from every historical source version.
- Canary bounded batches before expanding throughput.
- Pause enqueueing if migration harms interactive queue latency.
- Track success, blocked reasons, render duration, memory, output size,
  verification failures, duplicate suppression, and storage cleanup.
- Keep flag rollback until the new authoring path and the backfilled playback
  population complete their observation windows.

## Exit criteria

1. Dry-run inventory classifies the full production population.
2. Every historical source version passes representative sandbox rendering,
   verification, save, and byte-range playback.
3. Duplicate enumeration creates no duplicate job, blob, generation, or
   billing.
4. Every legacy video is `Backfilled` or `Already migrated`; none is `Blocked`.
5. Every migrated Artifact streams a verified MP4 and no client executes stored
   scene code.
6. Original source remains available only through the approved rollback window.
7. The new authoring path has completed its production observation window.
8. Phase 8 receives evidence that legacy generation and browser scene playback
   are no longer required.
