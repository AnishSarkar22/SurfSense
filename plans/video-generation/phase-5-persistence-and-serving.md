# Phase 5 — Persistence, storage, and playback

**Status:** Implemented, with a known final-link transaction gap.

## Receipt-bound save

The verified MP4 is the only durable video output. The executor passes an `ArtifactFileStreamInput` to generic `save_artifact()`:

```text
chunks          = sandbox.read_file_stream(output_path)
filename        = attempt MP4 filename
mime_type       = video/mp4
expected_sha256 = signed verification receipt digest
format          = video
```

Generic storage streams without buffering the complete file in backend memory, computes byte count and SHA-256 while writing, supports local and Azure backends, rejects digest mismatch, and removes a partially stored blob when save fails.

The PRIMARY file is the MP4. Narration, `props.json`, risk stills, contact sheet, progress/cancel files, render metadata, verification receipt, and copied runtime are temporary attempt data and are removed best-effort after a successful save.

## Artifact metadata

Saved video metadata records:

- verification availability/reason and primary SHA-256;
- video schema version;
- capability `build_id`;
- video skill SHA-256 and exact loaded skill files;
- selected capability IDs;
- complete renderer sidecar metadata.

Revisions target an existing video Artifact in the same workspace and use its current generation for optimistic concurrency. They create a new verified generation; bytes are never edited in place.

## Job completion boundary

Current completion has two commits:

1. `save_artifact()` commits the Artifact/blob.
2. The Celery task separately links `artifact_id` and marks `DeliverableJob.ready`.

A ready job cannot lack an Artifact ID, but an Artifact can be committed if the second transition fails. There is no implemented atomic save/link transaction or compensation reconciler for this narrow window.

Cancellation and supersession are checked through attempt-bound heartbeats and the worker watcher before normal completion. Worker `finally` still terminates the exact attempt sandbox even when cleanup commands fail.

## Existing delivery path

No job-specific media endpoint or video storage subsystem was added. Existing authenticated Artifact routes provide:

- manifest lookup and PRIMARY `video/mp4` content URL;
- full `200` responses;
- single closed and open-ended byte ranges with `206`;
- inclusive `Content-Range` and `Accept-Ranges: bytes`;
- `416` for unsatisfiable ranges;
- ETag behavior and inline disposition;
- workspace authorization and existing download.

Local storage seeks to the requested range; Azure uses ranged blob download. Multipart ranges are not implemented. The shared Video.js component receives the generic content URL directly, uses `preload="none"`, and relies on browser Range requests for seeking.

## Evidence

Storage and route tests cover streaming size/digest checks, partial cleanup, manifest/download, full content, `206`, `416`, ETag, authorization, and local/Azure range behavior. Executor coverage asserts the signed receipt digest is passed as `expected_sha256`, revision generation is enforced, and capability/skill/render metadata is saved.
