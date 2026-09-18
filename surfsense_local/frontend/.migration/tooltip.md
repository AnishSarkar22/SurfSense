# tooltip

2026-09-18 — golden pair via registry for the structure, project styling and
defaults replayed by hand. Migrated; typecheck clean, tests back at baseline
parity (they were not, at first — see Behavior changes).

## Changed

- `src/components/ui/tooltip.tsx` — rewritten onto `@base-ui/react/tooltip`:
  - `Portal > Content` became `Portal > Positioner > Popup`. The Positioner
    carries `isolate z-50`; the Popup keeps the project's styling.
  - Positioning props are declared, destructured and forwarded explicitly:
    `side`, `sideOffset`, `align`, `alignOffset` and `collisionPadding` are
    `Pick`ed from `Positioner.Props` and passed to the Positioner. Left in
    `...props` they would have landed on the Popup and silently stopped
    positioning anything. `collisionPadding` is in the list because seven call
    sites pass it.
  - Provider: `delayDuration = 500` → `delay = 500`.
  - `disableHoverableContent` has no Provider equivalent in Base UI; it moved to
    the Root wrapper as `disableHoverablePopup = true`, preserving the same
    behavior (the popup is never a hover target).
  - Class hooks: `data-[state=closed]:*` → `data-closed:*`, and
    `data-[state=delayed-open]:*` → `data-open:*`. The `data-[side=*]` slide
    classes are unchanged — `data-side` survives the migration.
  - `TooltipContent` now spreads onto the Popup, so a call site's `className`
    still lands on the styled box.
- Thirteen call sites across nine files: `<TooltipTrigger asChild><El …>kids</El>
  </TooltipTrigger>` → `<TooltipTrigger render={<El … />}>kids</TooltipTrigger>`
  in `studio-panel.tsx`, `settings-dialog.tsx`, `artifact-list.tsx` (2),
  `chat-composer.tsx`, `message.tsx`, `workspace-rail.tsx` (3),
  `dashboard-page.tsx`, `update-settings.tsx`, `sources-panel.tsx` (2).
  `relative-time.tsx:129` passed a prebuilt element and became
  `<TooltipTrigger render={time} />`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over
`tooltip.tsx` and all nine consumers returns nothing.

## Left alone

- `main.tsx:29` and `test-utils.tsx` mount `<TooltipProvider>` with no props;
  the new `delay` default covers them.

## Behavior changes

- **The popup is no longer a `role="tooltip"` element in Base UI, and the
  trigger gets no `aria-describedby`.** This is deliberate upstream: Base UI's
  own docs (`docs/react/components/tooltip.md:390`) call tooltips visual-only
  and tell you to put an `aria-label` on the trigger instead. Seven existing
  tests assert `getByRole("tooltip", { name })`, so this project has the
  opposite contract. The wrapper now passes `role="tooltip"` on the Popup,
  which restores the role and the accessible name and returns the suite to
  baseline — the tests were NOT rewritten to fit the library.
  Still flagged, not patched: the `aria-describedby` link from trigger to
  popup is gone and cannot be restored from the wrapper. Screen-reader users
  will no longer hear the tooltip text when focusing a trigger, so every
  icon-only trigger needs its own `aria-label`. Most already have one; auditing
  the rest is a follow-up.
- `onOpenChange` now receives `(open, eventDetails)`. No call site uses the
  second argument.
- Radix's `skipDelayDuration` (300ms grouping window) is `timeout` in Base UI
  and defaults to 400ms. Nothing sets it, so moving between two triggers now
  stays "instant" for 100ms longer.
- Base UI's Trigger also honours per-trigger `delay`/`closeDelay`; unused here.

## Verify by hand

1. Hover the workspace rail buttons: the tooltip should appear to the right
   after ~500ms, and moving the pointer onto the tooltip itself should not keep
   it open.
2. Hover a failed source or artifact row, then hold Ctrl/Cmd — the error
   tooltip should swap in above the row, positioned with its 8px collision
   padding away from the panel edge.
3. Settings dialog → the "More about importing" info button: the tooltip should
   stay inside the dialog (12px collision padding) and wrap at `max-w-64`.
4. Check that focus-only (keyboard) tab to an icon button still announces
   something useful — the tooltip no longer describes it.
