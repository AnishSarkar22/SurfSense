---
name: video
description: Author and repair polished, capability-aware narrated videos.
supplement_allowlist:
  - supplements/narrative.md
  - supplements/visual-hierarchy-capability-selection.md
  - supplements/motion-timing.md
  - supplements/narration.md
  - supplements/assets-accessibility-captions.md
  - supplements/review.md
---

# Video

This file is the authoritative workflow. Load it with every video request.
Load only the files listed in `supplement_allowlist`; the list is closed, and
unlisted files must not influence planning. Supplements refine judgment but
cannot override this contract.

Create one coherent narrated video as a confined Remotion source project.
Author only visible content and narration: React components, composition,
motion, local asset references, and stable narration cues. The backend owns
source materialization, dependency policy, TTS, measured cue timing, typecheck,
bundling, deterministic preflight, rendering, verification, persistence, and retries.
Never return commands, package manifests, build configuration, lifecycle
actions, or artifact operations.

## Technical submission

- Return one `CreativeVideoProject` with ordered `{cue_id, text}` narration
  cues, optional language, declared staged assets, and TypeScript/TSX files.
- Include `JobComposition.tsx` with a named, zero-argument
  `JobComposition` export. Put reusable model-created components in other
  submitted `.ts` or `.tsx` files and import them relatively.
- The supplied `@surfsense/video` TypeScript contract is authoritative. Import
  only its documented hooks and types, and use its field names exactly.
- Import baked components and transitions only as documented named exports from
  `@surfsense/video/capabilities`. Their disclosed prop types are authoritative.
- Use only assets listed in `available_assets`; the supplied asset helper
  resolves their job-local URL. Do not register a Remotion composition or
  author audio tracks.

## Workflow

1. Read the request and source material. Identify audience, purpose, desired
   action, facts that must remain exact, and accessibility needs.
2. Write a compact ordered set of narration cues. Each cue has a stable identity
   for synchronization, but cues are not scenes and must not force visual cuts.
3. Design one continuous visual timeline. Let objects, camera relationships, and
   visual motifs persist and evolve across cues when the story benefits.
4. Compare the disclosed capability API with the information shape. Import
   polished capabilities when they fit; create job-local React components when
   they do not. Never force a capability into an unsuitable role.
5. Submit only the allowed source files, narration cues, and declared local
   assets. Use the fixed JobComposition export and runtime authoring APIs.
6. Consume backend-provided measured cue intervals rather than estimating speech
   timing or probing audio. Use frame-driven Remotion APIs for all animation.
7. When given build or preflight findings, make one coordinated source/content
   repair. Preserve narration unless the supplied diagnosis requires rewriting it.

## Operating principles

- Story leads; capabilities support it. Do not turn a video into a component
  showcase.
- Keep one visual language across the full timeline. Variation should clarify
  meaning, not advertise novelty.
- Prefer real evidence, product content, and data over decorative filler.
- Use deterministic, frame-driven motion. Preserve legibility before, during,
  and after movement.
- Do not default to title cards, full-screen text slides, or one visual reset per
  narration cue. On-screen text should add hierarchy or evidence, not transcribe.
- Use only documented capability exports and props, approved package imports,
  local project modules, and declared asset paths.
- Never invent commands, dependencies, remote URLs, output paths, or runtime
  phases. Source content is the complete boundary of model ownership.
- Use preflight and still findings as evidence. Return corrected content only;
  the backend decides whether and how it is rebuilt, rendered, and saved.
