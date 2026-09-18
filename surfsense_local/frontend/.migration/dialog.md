# dialog

2026-09-18 — golden pair via registry; the wrapper was the stock radix-nova
variant apart from three project deltas, so the base-nova variant was taken and
those deltas replayed. Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/dialog.tsx` — rebuilt from the base-nova golden:
  `DialogPrimitive.Overlay` → `Backdrop`, `DialogPrimitive.Content` → `Popup`.
  A centered modal needs no Positioner, so the anatomy stays
  `Portal > Backdrop + Popup`. Props types moved to `DialogPrimitive.*.Props`.
  The close button is now `<DialogPrimitive.Close render={<Button … />}>` with
  the icon as the Close's children.
- The three project deltas were preserved: `Button`/`cn` imports from the app's
  own paths, the project's `XIcon` in place of the registry's
  `IconPlaceholder`, and `font-heading` (not `cn-font-heading`) on
  `DialogTitle`.
- Four call sites moved off `onOpenAutoFocus`, which Base UI replaces with the
  Popup's `initialFocus`:
  - `chats-dialog.tsx:63` and `workspace-rail.tsx:97` focused and *selected* an
    input. They now pass a function that focuses and selects by hand and
    returns `false` (Base UI's "don't move focus yourself" signal) — the same
    net effect as Radix's `preventDefault()` plus manual focus.
  - `chats-dialog.tsx:160` and `connection-card.tsx:333` only focused a search
    box, so they pass the ref directly: `initialFocus={searchRef}`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over `dialog.tsx`
and the four consumers returns nothing.

## Left alone

- No consumer passes `asChild` to `DialogTrigger` or `DialogClose`, so no
  trigger rewrites were needed here.
- `detail-panel.tsx` and `modal-layout.test.tsx` were touched only where the
  test asserted a Radix-only attribute (see alert-dialog's report).

## Behavior changes

- `data-scroll-locked` is gone from `<body>`. Radix marked the locked body with
  that attribute; Base UI locks by writing `overflow: hidden` inline and adding
  `scrollbar-gutter: stable` on `<html>`. Nothing in the app's CSS keyed off it
  — only `modal-layout.test.tsx` did, and that assertion now checks the lock
  itself instead of the marker.
- Base UI never writes padding onto `<body>` to compensate for the scrollbar,
  so the Electron title-bar padding on `#root` is unaffected (which is what
  that test exists to protect).
- `onOpenChange` now receives `(open, eventDetails)`; the reason codes
  (`escape-key`, `outside-press`, …) replace Radix's `onEscapeKeyDown` /
  `onPointerDownOutside`. No call site used those.

## Verify by hand

1. Rename a chat (chats list → row menu → Rename): the dialog should open with
   the current name focused AND fully selected, so typing replaces it.
2. Open the chats dialog and the model browser: the search box should take
   focus on open.
3. Press Escape and click the backdrop — both should close, and focus should
   return to the control that opened the dialog.
4. In the packaged macOS app, open any dialog and confirm the title-bar strip
   still has its 28px and the background does not shift sideways.
