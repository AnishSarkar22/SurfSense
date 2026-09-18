# context-menu

2026-09-18 — golden pair via registry, project deltas replayed. Migrated;
typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/context-menu.tsx` — rebuilt from the base-nova golden on
  `@base-ui/react/context-menu`. Same anatomy change as dropdown-menu:
  `Content` → `Portal > Positioner > Popup` with the positioning props
  forwarded to the Positioner, `Label` → `GroupLabel`, `ItemIndicator` →
  `CheckboxItemIndicator`/`RadioItemIndicator`, `Sub*` → `Submenu*`, and the
  `--radix-context-menu-*` vars → `--available-height` / `--transform-origin`.
  Project deltas kept: local `CheckIcon`/`ChevronRightIcon`, no
  `cn-menu-target cn-menu-translucent` classes, `ml-auto` on the submenu
  chevron.
- `workspace-rail.tsx:172` — `<ContextMenuTrigger asChild>` → `render={…}`.
- `workspace-rail.tsx:206,210` — the two items' `onSelect` → `onClick`.
- `workspace-rail.tsx:208` — `onCloseAutoFocus={(e) => e.preventDefault()}` →
  `finalFocus={false}`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over
`context-menu.tsx` and `workspace-rail.tsx` returns nothing.

## Left alone

- `workspace-rail.tsx` also hosts tooltips, a dialog and an alert dialog; those
  were migrated in their own steps and only the context-menu parts changed
  here.

## Behavior changes

- **`modal={false}` is gone.** The wrapper used to default the Root to
  non-modal. Base UI's `ContextMenu.Root.Props` explicitly omits `modal`
  (`context-menu/root/ContextMenuRoot.d.ts:13`), so the prop cannot be
  forwarded and the library's own modality applies. Flagged, not worked around:
  the visible effect is whether the page behind the open menu stays
  scrollable/interactive. Worth a look on the workspace rail, which is the only
  context menu in the app.
- Item selection is `onClick` + `closeOnClick` rather than `onSelect` with
  `preventDefault`, exactly as in dropdown-menu.

## Verify by hand

1. Right-click a workspace in the rail: Rename and Delete should both open
   their dialogs and the menu should close.
2. With the menu open, check whether the rest of the app is still scrollable —
   this is the `modal` change above.
3. After Rename, focus should land in the rename dialog's input, not back on
   the workspace button.
