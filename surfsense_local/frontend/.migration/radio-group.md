# radio-group

2026-09-18 — golden pair via registry; wrapper was pristine apart from its `cn`
import. Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/radio-group.tsx` — the group now comes from
  `@base-ui/react/radio-group` (callable, no `.Root`), and the item from
  `@base-ui/react/radio`: `RadioGroupPrimitive.Item` → `RadioPrimitive.Root`,
  `RadioGroupPrimitive.Indicator` → `RadioPrimitive.Indicator`. Props types are
  `RadioGroupPrimitive.Props` and `RadioPrimitive.Root.Props`.
- `disabled:cursor-not-allowed disabled:opacity-50` → `data-disabled:*`, for the
  same reason as checkbox: Base UI's Radio Root renders a `<span>`
  (`radio/root/RadioRoot.js:204`).

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" radio-group.tsx` returns
nothing.

## Left alone

- `quiz-viewer.tsx` and `model-list.tsx` call sites: `value`, `onValueChange`,
  `disabled`, `id` and `aria-label` all carry over.

## Behavior changes

- The item's `data-checked:border-primary data-checked:bg-primary
  data-checked:text-primary-foreground` classes start working. Tailwind v4
  compiles `data-checked:` to a literal `[data-checked]` selector, which Radix
  never emitted (it uses `data-state="checked"`), so under Radix these three
  rules were dead. Base UI emits `data-checked`, so a selected radio now also
  gets the primary border/fill behind its dot. This was inherited from the
  registry, not introduced here — but it is a visible change and worth a look.
- `onValueChange` now receives `(value, eventDetails)` instead of `(value)`.
  Both call sites take only the first argument.

## Verify by hand

1. Studio → a quiz artifact: pick an answer and confirm the selected radio
   looks right (see the note above — the fill is new), then that revealing the
   answer disables the group.
2. Settings → Models → the model list: click a row's label text and confirm the
   radio selects, which exercises the hidden-input `htmlFor` association.
3. Arrow-key through the list; selection should follow focus as before.
