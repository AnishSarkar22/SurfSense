# dropdown-menu

2026-09-18 — golden pair via registry (Radix `DropdownMenu` → Base UI `Menu`),
project deltas replayed, plus the largest consumer sweep of this migration.
Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/dropdown-menu.tsx` — rebuilt from the base-nova golden on
  `@base-ui/react/menu`:
  - `Content` → `Portal > Positioner > Popup`, with `side`/`sideOffset`/
    `align`/`alignOffset` declared, destructured and forwarded to the
    Positioner.
  - `Label` → `GroupLabel`, `ItemIndicator` → `CheckboxItemIndicator` /
    `RadioItemIndicator`, `Sub`/`SubTrigger` → `SubmenuRoot`/`SubmenuTrigger`,
    `SubContent` rebuilt on top of `DropdownMenuContent`.
  - CSS vars: `--radix-dropdown-menu-content-available-height` →
    `--available-height`, `--radix-dropdown-menu-trigger-width` →
    `--anchor-width`, `--radix-dropdown-menu-content-transform-origin` →
    `--transform-origin`.
  - Project deltas kept: `modal = false` default on the Root, the app's own
    `CheckIcon`/`ChevronRightIcon` in place of `IconPlaceholder`, no
    `cn-menu-target cn-menu-translucent` surface classes, `ml-auto` (not
    `cn-rtl-flip ml-auto`) on the submenu chevron.
- Eight `<DropdownMenuTrigger asChild>` call sites became `render={…}`
  (`artifact-list.tsx` ×2, `score-screen.tsx`, `chats-dialog.tsx`,
  `model-picker.tsx`, `thread-panel.tsx`, `sources-panel.tsx`).
- **`onSelect` → `onClick` on 19 menu items** across six files. Base UI's
  `Menu.Item` has no `onSelect`; it fires `onClick` and closes according to
  `closeOnClick` (default `true` on Item, matching Radix). The codemod only
  touched `DropdownMenu*Item` tags — the app's own `onSelect` props elsewhere
  (`studio-panel.tsx`, `workspace-rail.tsx`, `chats-dialog.tsx` row props) are
  untouched.
- `artifact-list.tsx:302` dropped `onSelect={(e) => e.preventDefault()}` on the
  filter's CheckboxItem: Base UI's CheckboxItem defaults to `closeOnClick:
  false`, so staying open is now the default rather than something to force.
- `model-picker.tsx:142` gained `closeOnClick` on its RadioItem for the
  opposite reason: Radix closed the menu when a radio was picked, Base UI's
  RadioItem does not. The picker's whole flow (pick a model, menu closes)
  depends on it.
- `artifact-list.tsx:291` — `<DropdownMenuLabel>` moved INSIDE
  `<DropdownMenuGroup>`. Base UI's `GroupLabel` throws
  ("MenuGroupContext is missing") outside a Group; Radix's Label did not care.
  This crashed the whole filter menu, not just the label.
- Two `onCloseAutoFocus` handlers became Base UI's Popup `finalFocus`:
  `thread-panel.tsx:229` (returns `false` only when renaming has already moved
  focus into the title field) and `chats-dialog.tsx:293`
  (`finalFocus={false}`).
- Tests: menu queries that ran synchronously right after the trigger click
  (`screen.getByRole("menuitem"…)`) became `await screen.findByRole(…)` in five
  test files. Base UI mounts the portal a tick later than Radix did; the
  assertions themselves are unchanged.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over
`dropdown-menu.tsx` and its consumers returns nothing.

## Left alone

- `workspace-rail.tsx:211,217` still use `<ContextMenuItem onSelect>` — that is
  the context-menu wrapper, still on Radix, migrated in its own step.
- `model-picker.tsx`'s `DropdownMenuLabel`s are already inside their Group.

## Behavior changes

- Menu items no longer close the menu via `onSelect`'s `preventDefault`; the
  knob is `closeOnClick`. Defaults differ per part: Item `true` (same as
  Radix), CheckboxItem and RadioItem `false` (Radix closed both). Every current
  call site has been set to match its old behavior, but new code should pass
  `closeOnClick` deliberately.
- `onCheckedChange` and `onValueChange` now receive an `eventDetails` second
  argument.
- The submenu trigger's open marker is `data-popup-open`, not
  `data-[state=open]`; nothing in this app styled on it.

## Verify by hand

1. Studio → an artifact's ⋯ menu: Open / Regenerate / Cancel / Delete should
   each run and close the menu.
2. Studio → Filter artifacts: check one type, then a second WITHOUT the menu
   closing; "Clear filter" should close it.
3. Composer → model picker: search, pick a model — the menu must close and the
   button label update. Reopen and click "Manage models".
4. Chats list → a row's ⋯ menu → Rename: the title field should take focus and
   keep it (the menu must not steal focus back).
5. Sources → a processing source's ⋯ menu: Delete is disabled; Escape closes.
