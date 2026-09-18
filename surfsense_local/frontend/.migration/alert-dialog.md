# alert-dialog

2026-09-18 — golden pair via registry, with one deliberate divergence from the
base-nova golden (see below). Migrated; typecheck clean, tests at baseline
parity.

## Changed

- `src/components/ui/alert-dialog.tsx` — rebuilt from the base-nova golden:
  `Overlay` → `Backdrop`, `Content` → `Popup`, `Cancel` → `Close`. Props types
  moved to `AlertDialogPrimitive.*.Props`. Project deltas replayed: local
  `Button`/`cn` imports and `font-heading` on the title.
- `AlertDialogAction` **diverges from the golden**. The registry's base variant
  makes Action a plain `<Button>`, which no longer closes the dialog — Base UI
  has no Action part. Nine call sites in this app rely on Radix's
  close-on-click (delete artifact, delete workspace, delete sources, reset
  flashcards, …), so Action is instead
  `<AlertDialogPrimitive.Close render={<Button variant size />}>`. That keeps
  both Radix behaviors: it closes by default, and a handler can still keep it
  open.
- `egress-prompt.tsx:107` and `model-catalog-page.tsx:550` did exactly that,
  with `event.preventDefault()`. Base UI's Close does not read
  `defaultPrevented`; its merged handlers stop at
  `event.preventBaseUIHandler()` (`merge-props/mergeProps.js:19`), so both now
  call that. Without the swap, both dialogs closed mid-request and their
  spinners vanished — the egress prompt's retry then failed with the original
  403.
- Two `<AlertDialogTrigger asChild>` call sites (`connection-card.tsx:267`,
  `flashcards-viewer.tsx:194`) became `render={<Button … />}`.
- `modal-layout.test.tsx` — the shared dialog/alert-dialog layout test asserted
  `document.body.hasAttribute("data-scroll-locked")`, a Radix-only marker. It
  now asserts the lock itself (`overflow-y: hidden` on the body) and tolerates
  jsdom reporting an unset padding as `"0"` rather than `"0px"`. The test's
  actual subject — Electron title-bar padding staying on `#root` and off the
  body — is unchanged and still enforced.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over
`alert-dialog.tsx` and both trigger consumers returns nothing.

## Left alone

- The seven Action call sites that do not prevent closing: they keep working
  because Action still closes.
- `AlertDialogMedia`, `AlertDialogHeader`, `AlertDialogFooter` — plain divs.

## Behavior changes

- Focus on open moves. Radix focused the Cancel button by default; Base UI
  focuses the first tabbable element in the popup. For these dialogs that is
  usually still Cancel (it is the first footer button), but confirm on the ones
  with links or inputs in the body. `initialFocus` on the Popup is the knob if
  a specific dialog needs Cancel back.
- `onOpenChange` gains its `eventDetails` argument, as with dialog.

## Verify by hand

1. Studio → delete an artifact: the dialog must close when you confirm, and the
   artifact disappears.
2. Trigger an egress prompt (an action that hits a blocked host) and click
   Allow: the dialog must STAY open with a spinner until the retry finishes,
   then close on its own.
3. Model catalog → delete a model: same stay-open-then-close behavior.
4. Open any of these dialogs and press Escape immediately — check which button
   had focus when it opened.
