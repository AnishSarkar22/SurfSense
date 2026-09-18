# label

2026-09-18 — golden pair via registry; wrapper was pristine apart from its `cn`
import. Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/label.tsx` — Base UI has no Label primitive, so
  `LabelPrimitive.Root` became a native `<label>` and the props type became
  `React.ComponentProps<"label">`. Classes, `data-slot="label"` and every
  consumer are unchanged.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" label.tsx` returns nothing.

## Left alone

- `field.tsx`'s `FieldLabel` keeps importing this `Label`; nothing there needed
  to change.

## Behavior changes

- Radix's Label primitive suppressed text selection on double-click and
  forwarded clicks to the associated control for non-labelable elements. A
  native `<label>` keeps `htmlFor` association (the only behavior this app uses)
  but no longer prevents double-click text selection. The wrapper's
  `select-none` class already covers that visually.

## Verify by hand

1. In Settings → Network, click the label text next to a checkbox — the
   checkbox should still toggle.
2. Double-click a label: no text selection should appear.
