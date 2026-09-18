# separator

2026-09-18 — golden pair via registry; wrapper was pristine apart from its `cn`
import. Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/separator.tsx` — `SeparatorPrimitive.Root` →
  the callable `Separator` from `@base-ui/react/separator`; props type is now
  `SeparatorPrimitive.Props`. The `decorative` prop was removed (no Base UI
  equivalent); no call site passed it — the wrapper's own `decorative = true`
  default was the only use.
- `data-horizontal:` / `data-vertical:` classes are untouched: Tailwind v4
  compiles them to `[data-orientation=horizontal|vertical]`, and Base UI's
  Separator emits `data-orientation` exactly as Radix did (verified in the
  built CSS).

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" separator.tsx` returns
nothing.

## Left alone

- `button-group.tsx`'s `ButtonGroupSeparator` and `detail-panel.tsx` /
  `field.tsx` consumers: they pass only `orientation` and `className`.

## Behavior changes

- Accessibility role changes. Radix with `decorative={true}` (this project's
  default for every separator) renders `role="none"`, hiding the element from
  assistive tech. Base UI's Separator always renders `role="separator"` with
  `aria-orientation` (`separator/Separator.js:31`). Every separator in the app
  is now announced. Flagged, not patched — there is no `decorative` escape
  hatch in Base UI; the fix, if the noise matters, is `aria-hidden` at the call
  site.

## Verify by hand

1. Look at the detail panel and the settings dialog: horizontal rules should
   still be 1px and full-width, vertical ones 1px and self-stretched.
2. With a screen reader on, tab through the settings dialog and confirm the
   extra "separator" announcements are acceptable.
