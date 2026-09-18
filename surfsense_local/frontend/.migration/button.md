# button

2026-09-18 — golden pair via registry (radix-nova vs base-nova), hand-replayed
onto the project's customized wrapper. Migrated; typecheck clean, tests at
baseline parity.

## Changed

- `src/components/ui/button.tsx` — `Slot` + `asChild` replaced by the real
  `@base-ui/react/button` primitive; props type is now
  `ButtonPrimitive.Props & VariantProps<typeof buttonVariants>`; the
  `React`/`Slot` imports are gone. The project's customizations were kept
  verbatim: `cursor-pointer` in the base class, the `xl`/`2xl`/`icon-xl`/
  `icon-2xl` sizes, and `cn` from `@/lib/utils`.
- `src/components/ui/button.tsx:64-65` — `data-variant` / `data-size` kept
  deliberately. The base-nova golden drops both, but
  `model-catalog.test.tsx:502` and `left-sidebar.test.tsx:42` assert them, and
  `card.tsx` / `field.tsx` select on the same convention. Re-added after the
  replay.
- `src/components/ui/alert-dialog.tsx:157,177` — `AlertDialogAction` /
  `AlertDialogCancel` wrapped their Radix part in `<Button asChild>`; now
  `<Button render={<AlertDialogPrimitive.Action … />} />`. The Radix parts
  themselves are untouched — alert-dialog is still on Radix and migrates later.
- `src/features/studio/artifact-panel.tsx:43-62` — the per-file download was
  `<Button asChild><a download …/></Button>`. It is now a plain `<a>` carrying
  `buttonVariants({ variant: "secondary", size: "icon-sm" })` plus the same
  `data-slot`/`data-variant`/`data-size` attributes Slot used to merge onto it.
  See "Behavior changes" for why this did not become `render`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild"` over
`button.tsx` and `artifact-panel.tsx` returns nothing. (`grep` must run with
`-a` or `LC_ALL=C` in this project — `combobox.tsx` contains literal NUL bytes
at lines 351/354, so a UTF-8 grep silently skips it.)

## Left alone

- `alert-dialog.tsx`'s Radix primitive parts — that component has its own
  migration step; only its two Button call sites changed here.
- Every other `ui/` wrapper: 16 remain on Radix.
- `components.json` still reads `radix-nova`; it flips to `base-nova` once the
  last wrapper is migrated, so `shadcn add` keeps matching the majority of the
  tree in the meantime.

## Behavior changes

- Base UI's Button only accepts a non-`<button>` element via `render` together
  with `nativeButton={false}`, and that mode adds `role="button"`
  (`internals/use-button/useButton.js:186`). Applying it to the artifact
  download turned the anchor into a button for assistive tech and broke
  `artifact-panel.test.tsx:54`, which asserts `getByRole("link")`. The
  `buttonVariants()` anchor above keeps link semantics; DOM and role are
  unchanged from the Radix version.
- No other delta: the Radix Slot path and the Base UI primitive both render a
  native `<button>` with the same attributes for every remaining call site.

## Verify by hand

1. Click any ordinary button (sidebar "New chat", settings actions) — hover,
   active `translate-y-px`, and focus ring should look unchanged.
2. Tab to a disabled button: it should still be skipped (Base UI's
   `focusableWhenDisabled` defaults to false, matching Radix).
3. Open an alert dialog (delete a connection, reset flashcards) and confirm
   Action/Cancel still look like buttons and still close the dialog.
4. Open a studio artifact with files and click the download icon — it must
   download, and a screen reader should announce it as a link.
