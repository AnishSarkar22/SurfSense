# combobox

2026-09-18 — transformation engine on the project's own file. Migrated;
typecheck clean, build clean, tests at baseline parity.

## Changed

- `src/components/ui/combobox.tsx` — this is a hand-rolled combobox (its own
  context, filtering, roving `aria-activedescendant`) that used Radix's Popover
  for the popup. The popup moved to `@base-ui/react/popover`:
  - `Portal > Content` → `Portal > Positioner > Popup`, with `align` and
    `sideOffset` forwarded to the Positioner and the Portal keeping its
    `container` prop (still needed: inside a modal Dialog the list must be
    portalled within the dialog or the scroll lock swallows its wheel events).
  - **`Popover.Anchor` has no Base UI equivalent.** The wrapper used it to
    anchor the popup to the whole input group rather than the chevron button.
    The replacement is an `anchorRef` on the combobox context, attached to the
    `InputGroup` and passed to the Positioner's `anchor` prop — same anchor,
    same width behavior.
  - `onOpenAutoFocus` / `onCloseAutoFocus` `preventDefault` (keep focus in the
    input so typing keeps filtering) → `initialFocus={false}` /
    `finalFocus={false}` on the Popup.
  - CSS vars: `--radix-popover-content-available-height` →
    `--available-height`, `--radix-popover-trigger-width` → `--anchor-width`,
    `--radix-popover-content-transform-origin` → `--transform-origin`. The
    `w-(--anchor-width)` rule is what keeps the list the width of the input, so
    this rename was load-bearing.
  - The chevron `Popover.Trigger asChild` → `render={<InputGroupButton … />}`.
- The file's header comment was rewritten: it claimed the combobox was rebuilt
  on Radix "because this app does not depend on Base UI", which is no longer
  true.

Leftover scan clean — but note the trap: this file contains literal NUL bytes
at lines 351/354 (a `"\0"` keyword separator), so `file` calls it `data` and a
UTF-8 `grep -rn radix src` **silently skips it**. Verified with
`LC_ALL=C grep -an radix`, which returns nothing. Any future sweep of this repo
must use `grep -a` or `LC_ALL=C`.

## Left alone

- The combobox's own logic: filtering, keyboard handling, item registration,
  `ComboboxList`/`Group`/`Item`/`Empty` (plain divs). None of it was Radix.
- `input-group.tsx`, its only structural dependency, was never Radix.

## Behavior changes

- None expected; the single consumer (`connection-form.tsx:136`, the base-URL
  picker) uses the same wrapper API. Base UI's Popover, unlike Radix's, does
  not ship an Anchor part, so if a future call site wants to anchor elsewhere
  it must go through the context's `anchorRef`.

## Follow-up worth considering (not done here)

shadcn now ships a Combobox built on Base UI's own `Combobox` primitive, which
would replace this file's ~400 hand-written lines. That is a rewrite with its
own API surface, not part of a Radix→Base UI port, so it was left alone.

## Verify by hand

1. Settings → Models → Add an OpenAI-compatible connection: click the Base URL
   field, confirm the suggestion list opens flush with the field and at the
   same width.
2. Type to filter, arrow up/down through the list, press Enter — the value
   should land in the input and the list should close.
3. Do all of the above inside the dialog and scroll the list with the wheel:
   this is what the `container` prop protects.
