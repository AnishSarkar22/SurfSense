# Motion and timing

Motion should explain change and preserve comprehension.

- Use backend-provided measured narration cue intervals as the timing source of
  truth. Read them through the trusted authoring API.
- Author visual timing freely with interpolation, springs, and frame-driven
  components. Use `TimelineLayer` instead of raw `Sequence` for independently
  timed temporary visuals so their lifetime is explicit.
  Persistent visual systems may remain mounted across multiple narration cues.
- Respect each selected capability's documented natural motion. Do not speed an
  effect merely to fit overcrowded narration.
- Reserve entrances for establishing hierarchy, transitions for changes in
  thought, and exits for making room. Continuous motion needs a semantic reason.
- Sequence related elements in reading order. Keep stagger short enough that
  the viewer can perceive the group as one idea.
- Align important visual reveals with the phrase that explains them, allowing a
  small visual lead when it improves recognition.
- Prefer restrained easing and a few repeated motion motifs. Avoid simultaneous
  motion with unrelated directions, speeds, or spring character.
- Use deterministic seeds and frame-driven behavior. Never rely on runtime
  clocks, nondeterministic randomness, or interaction.
- Inspect the first content frame, cue boundaries, major visual events,
  capability keyframes, evenly spaced samples, and final content frame.
- Avoid resetting the full canvas at every cue. Persist and transform existing
  elements when continuity communicates the idea more clearly.
- When timing is tight, simplify layers or shorten copy before reducing
  readability or violating a capability's natural motion.
