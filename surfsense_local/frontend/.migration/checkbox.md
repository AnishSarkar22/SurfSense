# checkbox

2026-09-18 — transformation engine on the project's own file (the wrapper
predates the current registry variant, so the golden was used for
classification only). Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/checkbox.tsx` — import moved to
  `@base-ui/react/checkbox`; props type is `CheckboxPrimitive.Root.Props`.
  Root and Indicator part names are unchanged.
- Class hooks rewritten, and this was mandatory, not cosmetic:
  `data-[state=checked]:*` → `data-checked:*`, because Base UI emits a bare
  `data-checked` attribute (`checkbox/root/CheckboxRootDataAttributes.js`)
  instead of `data-state="checked"`. Left as-is, every checked style would
  have silently stopped applying.
- `disabled:cursor-not-allowed disabled:opacity-50` → `data-disabled:*`. Base
  UI's Checkbox Root renders a `<span>` plus a hidden `<input>`
  (`CheckboxRoot.js:241`), so the `disabled:` variant no longer has a disabled
  form control to match. (The shadcn base registry still ships the dead
  `disabled:*` classes here; that quirk was not copied.)

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|data-\[state=" checkbox.tsx`
returns nothing.

## Left alone

- Call sites in `network-settings.tsx`, `connection-form.tsx` and
  `sources-panel.tsx`: they pass `checked`, `onCheckedChange`, `disabled`,
  `id`, `aria-label` and `onClick`, all of which carry over unchanged.

## Behavior changes

- `onCheckedChange` now receives `boolean` rather than Radix's
  `boolean | "indeterminate"`. The call sites already narrowed with
  `checked === true`, so behavior is identical; the handlers are just wider
  than they need to be now.
- The root element is a `<span>`, not a `<button>`. Label association still
  works because Base UI moves the `id` onto the hidden input
  (`CheckboxRoot.js:174`), which is what `htmlFor` targets.

## Verify by hand

1. Settings → Network: toggle a host checkbox with the mouse and with Space.
2. Settings → Models → edit a connection with a saved key: the "Remove saved
   API key" checkbox should be disabled (dimmed, not clickable) while a new key
   is typed.
3. Sources panel: select a document by its checkbox and confirm the row click
   handler does not also fire.
