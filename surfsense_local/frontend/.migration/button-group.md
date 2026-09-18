# button-group

2026-09-18 — golden pair via registry, classification only for the styling;
the Slot part was transformed on the project's own file. Migrated; typecheck
clean, tests at baseline parity.

## Changed

- `src/components/ui/button-group.tsx` — `ButtonGroupText` was the file's only
  Radix user (`Slot.Root` behind `asChild`). It now renders through
  `useRender` + `mergeProps` with `defaultTagName: "div"` and a `render` prop.
  The `radix-ui` import is gone; `ComponentProps` from React is still used by
  the other parts.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild" button-group.tsx`
returns nothing.

## Left alone

- The `fieldset` root, the `m-0 min-w-0 border-0 p-0` classes and the
  `@/components/ui/separator` import: project customizations, kept verbatim.
- `buttonGroupVariants`. The base-nova golden rewrites these classes
  (`group/button-group` dropped, `[&>*:not(:first-child)]` replaced by
  `*:data-slot:` / `[&>[data-slot]~[data-slot]]`) — that is registry drift, not
  a Radix→Base UI requirement, so the project's classes stayed.
- The base-nova golden also gives `ButtonGroupText` a
  `state: { slot: "button-group-text" }`, adding a `data-slot` the Radix
  version never emitted. That was deliberately NOT copied: this file's
  `[&>[data-slot]:not(:has(~[data-slot]))]:rounded-r-lg!` rule selects on
  `data-slot`, so adding one would change which child gets the rounded corner.
  The two go together in the golden; taking one without the other would be a
  visual regression. `ButtonGroupText` is currently unused in the app.
- `ButtonGroupSeparator` still renders `@/components/ui/separator`, which is
  still Radix and migrates in its own step.

## Behavior changes

None. DOM output is identical for every call site.

## Verify by hand

1. Open a chat and look at the composer's `ButtonGroup` (thread-panel.tsx:201):
   the children should still sit flush with shared borders and a single
   rounded right edge.
2. Focus a control inside the group — the `*:focus-visible:z-10` lift should
   still raise it over its neighbours.
