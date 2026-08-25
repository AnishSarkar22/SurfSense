---
name: video
description: Plan and review polished, capability-aware narrated videos.
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

Create a semantic authored plan for one coherent narrated video. Author beats,
layers, utterances, assets, styles, pacing, and disclosed capability slots—not
executable source, imports, render commands, capability IDs, or frame counts.
Use only slots disclosed for the request and only props admitted by their
disclosed schemas. The backend compiler resolves slots, dependencies, build
identity, and timing.

## Workflow

1. Read the request and source material. Identify audience, purpose, desired
   action, facts that must remain exact, and accessibility needs.
2. Draft a compact creative outline as beats. Give each beat one narrative job
   and one dominant visual idea; remove any beat that merely repeats narration.
3. For each visual intent, compare disclosed capability metadata. Select the
   smallest compatible set of atoms, then compose them with core primitives.
4. Author and validate the complete semantic plan. Keep stable beat and utterance
   identities, complete narration sentences, explicit asset references, and
   capability slots. Express timing only as semantic pacing.
5. Synthesize the plan's utterances once with the existing TTS workflow. Treat
   measured audio duration as authoritative.
6. Compile the final timeline from measured narration. Respect capability
   natural-length floors, transition overlap, readable holds, safe margins, and
   deterministic timing. Do not estimate final frames from word counts.
7. Run preflight, then inspect the selected stills and contact sheet. Repair
   declarative visual data only; preserve approved narration unless the words
   themselves are wrong.
8. After preflight and still review pass, perform one full render.
9. Verify the rendered artifact, including picture, narration, captions,
   duration, frame coverage, and selected capability usage. Save only the exact
   artifact that passed verification.

## Operating principles

- Story leads; capabilities support it. Do not turn a video into a component
  showcase.
- Keep one visual language across the full timeline. Variation should clarify
  meaning, not advertise novelty.
- Prefer real evidence, product content, and data over decorative filler.
- Use deterministic, frame-driven motion. Preserve legibility before, during,
  and after movement.
- Never invent capability slots, props, assets, fonts, or timing behavior.
- A weak specialized match is a reason to use core primitives, not to force an
  unsuitable capability.
- Use preflight and still findings as evidence. Make the smallest coordinated
  repair, then recheck before rendering.
