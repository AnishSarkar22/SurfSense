# tabs

2026-09-18 — transformation engine on the project's own file (the wrapper is an
older shadcn baseline than the current registry variant, so the golden was used
for classification only). Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/tabs.tsx` — import moved to `@base-ui/react/tabs`.
  `TabsPrimitive.Trigger` → `TabsPrimitive.Tab`, `TabsPrimitive.Content` →
  `TabsPrimitive.Panel`; Root and List keep their names. Props types became
  `Root.Props`, `List.Props`, `Tab.Props` and `Panel.Props`. The public wrapper
  names (`TabsTrigger`, `TabsContent`) are unchanged, so no call site moved.
- Class hooks rewritten: `data-[state=active]:*` → `data-active:*`. Base UI
  marks the active tab with a bare `data-active` attribute instead of
  `data-state="active"`; without this the active tab would have lost its
  background, text color and shadow.
- Added `aria-disabled:pointer-events-none aria-disabled:opacity-50` alongside
  the existing `disabled:*` pair, matching the base-nova golden — Base UI's Tab
  surfaces disabled state through `aria-disabled` as well.

Leftover scan clean:
`grep -a "radix-ui\|@radix-ui\|data-\[state=" tabs.tsx` returns nothing.

## Left alone

- `score-screen.tsx` and `model-selection-content.tsx` call sites: they pass
  `value`, `onValueChange` and `className` only.
- `segmented-control.tsx` looks tab-like but is a plain project component with
  no Radix dependency.

## Behavior changes

- Keyboard activation flips from automatic to manual. Radix's Root defaulted to
  `activationMode="automatic"`, so arrow keys moved focus AND switched the
  panel. Base UI moved the knob to `List.activateOnFocus` and defaults it to
  `false`, so arrow keys now only move focus and Enter/Space activates.
  Flagged, not patched (the base registry accepts the new default); adding
  `activateOnFocus` to `TabsList` restores the old feel if you want it.
- `Panel` marks the hidden state (`data-hidden`) rather than the active one.
  Nothing in this project styles on that, but any future CSS should use the
  inverted polarity.
- `onValueChange` now receives `(value, eventDetails)`.

## Verify by hand

1. Studio → finish a quiz → the score screen: click through the
   correct/missed/skipped tabs, then arrow-key between them — note that the
   panel no longer follows focus until you press Enter.
2. Settings → Models: the local/cloud tab strip should still show the active
   tab with a background and shadow.
