# Review

Review against the intended communication, not merely technical validity.

## Source-content review

- Does every narration cue advance the story without forcing a visual reset?
- Are all claims supported, cue IDs stable, imports approved, and assets declared?
- Do capability choices fit the information, vibe, available duration, and
  continuous composition?
- Are narration, captions, assets, and visual emphasis mutually consistent?

## Preflight and still review

- Treat validation errors as source defects; do not work around them.
- Inspect supplied samples across the global timeline, especially cue
  boundaries, major visual events, evenly spaced frames, and first and last content.
- Check blank or duplicate frames, clipping, overflow, collisions, safe
  margins, contrast, caption clearance, reading order, and truthful data.
- Check coherence in the contact sheet: palette, typography, spacing, motion
  motifs, density, and progression should feel like one video.
- Make one coordinated source/content repair that addresses the root cause.
  Return corrected content only; backend code owns rebuilding and rechecking.

## Final verification

- Backend code performs the full render only after deterministic preflight.
- Backend verification proves that picture and narration are present, duration
  and frame coverage match measured cue timing, and imported capabilities resolve.
- Watch for defects stills cannot prove: audio cuts, pacing, transition
  discontinuity, caption drift, flicker, and unreadably brief holds.
- Never claim approval, save an artifact, or request another repair cycle.
  Acceptance and persistence belong exclusively to backend code.
