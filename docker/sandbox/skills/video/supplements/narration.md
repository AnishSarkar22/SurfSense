# Narration

Write for listening, then let measured speech determine the timeline.

- Give every narration cue a stable identity. Cue boundaries synchronize audio
  and visuals but do not define scenes or visual containers.
- Use complete, speakable sentences. Prefer concrete verbs, short clauses, and
  natural transitions over headings, fragments, or written-report phrasing.
- Make the narration intelligible without the picture while avoiding a literal
  reading of all on-screen text.
- Introduce unfamiliar terms before abbreviating them. Speak symbols, URLs,
  units, and numbers in forms a listener can understand.
- Keep claims faithful to the source. Preserve qualifiers and pronunciation
  cues where ambiguity would change meaning.
- Use the existing TTS workflow once for the complete set of utterances. Reuse
  the returned audio references exactly; do not source or synthesize narration
  another way.
- Treat measured audio duration as authoritative. Do not predict final cue or
  composition duration from character count, word count, or assumed speaking rate.
- If measured narration exceeds the duration budget, accept one narration-only
  repair using the supplied per-cue word budgets. Preserve cue identities,
  rewrite only changed narration, and leave source files untouched.
- If visual review fails, repair visuals without changing narration. Change an
  utterance only when its wording, factual accuracy, pronunciation, or meaning
  is itself defective; changed narration requires new measured audio timing.
- Leave enough visual quiet around dense spoken ideas. Silence and holds may
  support comprehension, but should not conceal missing content.
