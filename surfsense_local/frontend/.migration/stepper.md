# stepper

2026-09-18 — transformation engine (no registry counterpart: shadcn does not
ship a `stepper`, so there is no golden pair). Migrated; typecheck clean, tests
at baseline parity.

## Changed

- `src/components/ui/stepper.tsx:151-181` — `StepperTrigger` was the file's only
  Radix user (`const Comp = asChild ? Slot.Root : "button"`). It now renders
  through `useRender` + `mergeProps` with `defaultTagName: "button"`; its props
  type is `useRender.ComponentProps<"button">`, so the polymorphic escape hatch
  is `render` instead of `asChild`. `disabled`, the click handler and the
  `defaultPrevented` guard all moved into the merged props object unchanged.
- The `radix-ui` import is gone; `React` is still imported for the contexts and
  `forwardRef`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" stepper.tsx` returns
nothing.

## Left alone

- `StepperIndicator`'s `asChild` prop (line 185). Despite the name it never
  touched Radix — it is a local boolean that swaps the default number/check for
  the caller's children, and `onboarding-page.tsx:61` uses it that way. It is
  not a Radix API, so the migration did not rename it. Worth renaming later to
  something like `children`-driven, but that is a separate change.
- `StepperTrigger` has no consumers today; it is exported and was migrated for
  completeness.

## Behavior changes

None reached the app: the only migrated part is unused. If `StepperTrigger` is
adopted later, note that a non-`<button>` element passed through `render` will
not honour the `disabled` attribute the way a native button does — Base UI's
`Button` primitive with `nativeButton={false}` would be the right target then.

## Verify by hand

1. Run onboarding and step through it: the progress rail at the top should show
   the same filled/unfilled pills, since `StepperIndicator` is unchanged.
