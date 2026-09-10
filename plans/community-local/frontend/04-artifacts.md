# Frontend — Phase 4: Artifacts

> Owns: `features/artifacts/`. Routes: [`../api/04-artifacts.md`](../api/04-artifacts.md).
> Freshness: TanStack Query + SSE ([`../00-umbrella-plan.md`](../00-umbrella-plan.md)).

## Goal

An Artifacts surface: pick a format, pick documents, optional prompt → generate →
track → view or download. Separate from chat, one deliverable at a time.

## Work

Mirror `features/sources/` layout (page, hook, `api.ts`, components):

- **Entry** — an Artifacts section in the Sources panel, above All sources.
  Generated artifacts sit in a full-width row above a 3-column format grid
  with icons. Clicking an available card collapses the grid to Sources /
  Prompt / Generate. Hover shows the format `description`; an unavailable
  card keeps the `unavailable_reason` tooltip and does not open compose.
- **Format picker** from `GET /workspaces/{id}/artifacts/formats`. Image
  renders disabled when no image-generation role is selected, with a link to
  the OpenAI-compatible model setup. Infographic remains available with the
  generation role; the frontend does not infer availability from credentials.
- **Document picker** — multi-select over the workspace's sources (reuse the
  sources list) + an optional prompt / theme field.
- **Submit** → `POST /workspaces/{id}/artifacts/jobs`, returns the artifact id.
- **Track** with TanStack Query on `GET /artifacts/{id}`; SSE invalidates the
  document event for that id, `refetchInterval` is the fallback while running —
  the same freshness path as ingest, no bespoke polling loop.
- **Viewers by format**, a registry mirroring the worker's builders: summary →
  markdown; docx/pptx → preview PDF or download; xlsx → download; html →
  sandboxed iframe; mindmap → Markmap over the markdown; flashcards/quiz →
  interactive; podcast → audio player (streams `files/primary`); image →
  `<img>`; unknown → download link.
- **Library** — the workspace's artifacts, listing `ARTIFACT` documents that the
  sources view filters out (data-model list semantics), each opening its viewer.

## Acceptance

- Select documents → run a summary → the completed artifact renders inline; a
  docx/pptx downloads; a podcast plays.
- Image is unrunnable without a valid image-generation selection, with the
  reason and setup link shown.
- Infographic stays runnable with a generation model and does not ask for an
  image connection.
- A running job resolves on the SSE invalidation, not only on the poll.

## Needs from API / worker

The artifact routes and job completion — [`../api/04-artifacts.md`](../api/04-artifacts.md),
[`../worker/04-artifacts.md`](../worker/04-artifacts.md).
