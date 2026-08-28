# Visual hierarchy and capability selection

Choose capabilities from the disclosed public authoring API, then make the
composition read at a glance.

- Start from the current narrative purpose and information shape: comparison,
  sequence, metric, relationship, quote, interface state, or atmosphere.
- Treat `use_for` as positive evidence and `avoid_for` as a real warning.
  Compare category, tags, vibe, native canvas, natural length, and prop schema
  before importing a capability.
- Import only documented capability exports and use their declared props. Never
  import capability implementation paths or assume two components share an API.
- Prefer one expressive capability supported by quiet core primitives. Add a
  second atom only when it communicates a distinct relationship.
- Keep a coherent vibe. A deliberate contrast may mark a narrative turn, but
  unrelated visual dialects should not compete within one video.
- Match representation to data. Charts need honest scales and labels; interface
  treatments need plausible states; typography effects need short text.
- Establish one dominant element, one supporting level, and subdued context.
  Contrast through size, position, weight, and color before adding decoration.
- Protect safe margins and reading order. Avoid dense corners, equal emphasis
  everywhere, tiny labels, and important content beneath captions.
- Use `SpatialGrid` to reserve non-overlapping regions and `SpatialStack` for
  concurrently visible text or cards within a region. Do not independently
  absolute-position sibling text blocks. Animate inside each allocated region.
- Use `FittedText` for variable copy and choose width, line, and maximum-size
  bounds that preserve the intended hierarchy. Shorten copy before it becomes
  unreadable.
- Respect native canvas metadata and staging behavior. If a capability cannot
  remain legible and unclipped in its assigned region, adapt it or create a
  simpler job-local component.
- Use core primitives when no specialist is a strong semantic fit. Never force
  a capability merely because it is available.
