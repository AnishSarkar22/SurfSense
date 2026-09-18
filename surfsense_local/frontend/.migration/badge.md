# badge

2026-09-18 — golden pair via registry (radix-nova vs base-nova), replayed onto
a wrapper that was pristine apart from its `cn` import. Migrated; typecheck
clean, tests at baseline parity.

## Changed

- `src/components/ui/badge.tsx` — `Slot` + `asChild` replaced by `useRender` +
  `mergeProps`; props type is now `useRender.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants>`. `data-slot` / `data-variant` are no
  longer written as JSX attributes; they come from useRender's `state`
  (`{ slot: "badge", variant }`), which `getStateAttributesProps.js` converts
  to `data-slot="badge"` and `data-variant="<variant>"` — identical DOM.
  The project's `cn` import from `@/lib/utils` was kept; the badge variants are
  untouched.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui\|asChild" badge.tsx` returns
nothing. No consumer passed `asChild` to `<Badge>`, so no call sites changed.

## Left alone

Nothing related was skipped.

## Behavior changes

None. `openai-compatible-panel.test.tsx:230,308,314` assert
`data-variant` on rendered badges and still pass, which confirms the state →
data-attribute conversion produces the same markup as the Slot version.

## Verify by hand

1. Open Settings → Models → an OpenAI-compatible connection and check the
   role badges (chat / image / "unknown") still render with the right colors.
2. Any badge containing an icon: the `[&>svg]:size-3!` sizing should be
   unchanged.
