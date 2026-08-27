# Review

Review against the intended communication, not merely technical validity.

## Source-content review

- Does every narration cue advance the story without forcing a visual reset?
- Are all claims supported, cue IDs stable, imports approved, and assets declared?
- Do capability choices fit the information, vibe, available duration, and
  continuous composition?
- Are narration, captions, assets, and visual emphasis mutually consistent?

## Deterministic preflight

- Treat validation errors as source defects; do not work around them.
- When supplied deterministic build or preflight diagnostics, make one
  coordinated source/content repair that addresses the root cause.
- Return corrected content only; backend code owns rebuilding and rechecking.

## Final verification

- Backend code performs the full render only after deterministic preflight.
- Backend verification proves that picture and narration are present, duration
  and frame coverage match measured cue timing, and imported capabilities resolve.
- Author motion, pacing, transitions, and captions defensively because final
  acceptance is based on deterministic artifact checks, not visual-model judgment.
- Never claim approval, save an artifact, or request another repair cycle.
  Acceptance and persistence belong exclusively to backend code.
