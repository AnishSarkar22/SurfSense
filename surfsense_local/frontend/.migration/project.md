# project

2026-09-18 — whole-project Radix UI → Base UI migration of
`surfsense_local/frontend`, done wrapper by wrapper in dependency order.
17 of 17 wrappers migrated. **0 wrappers remain on Radix.**

## Order and method

Slot-only first (they unblock everything), then leaf primitives, then the
portal families:

1. `button`, `badge`, `button-group`, `stepper`
2. `label`, `separator`, `avatar`, `checkbox`, `radio-group`, `scroll-area`,
   `tabs`
3. `tooltip`, `dialog`, `alert-dialog`, `dropdown-menu`, `context-menu`,
   `combobox`

Each has its own report in this directory. Method per component: fetch the
radix-nova and base-nova variants from the shadcn registry, diff the project's
file against the radix one to separate customization from stock, then replay
the project's deltas onto the base variant — or, where the project's file
predated the current registry variant (`checkbox`, `tabs`, `stepper`,
`combobox`), transform the project's own file and leave its styling alone.

## Dependency swap

- `@base-ui/react@1.8.0` was already installed and unused; it is now the only
  primitive library.
- `radix-ui@1.6.7` removed from `package.json`; `pnpm install` run,
  lockfile updated.
- `components.json` style flipped `radix-nova` → `base-nova`, so future
  `shadcn add` delivers Base UI variants that match the tree.

## Verification against baseline

Baseline was recorded before any dependency or source change:

| | Baseline | After |
|---|---|---|
| `pnpm typecheck` | clean | clean |
| `pnpm test` | 7 failed / 146 passed (5 files) | 7 failed / 146 passed (5 files) — same tests |
| `pnpm lint` | 2 errors (`inline-citation.tsx:13`, `egress-prompt.tsx:51`) | same 2 errors |
| `pnpm build` | not run before | clean |

The 7 test failures and 2 lint errors are **pre-existing and unrelated**
(verified by stashing the migration and re-running lint). They are:
`app-bootstrap` ×1, `dashboard-page` ×3, `left-sidebar` ×1, `chats-dialog` ×1,
`model-catalog` ×1. One further `dashboard-page` test
("creates a thread on first send") is flaky in both directions and passes on a
focused run.

45 files changed, ~1090 insertions / ~1027 deletions.

## App-code sweep

The call-site surface was much larger than `asChild`:

- **`asChild` → `render`**: 26 call sites (13 tooltip triggers, 8 dropdown
  triggers, 2 alert-dialog triggers, 1 context-menu trigger, plus
  alert-dialog's own Action/Cancel and the artifact download).
- **`onSelect` → `onClick`** on 21 menu items, with `closeOnClick` set
  explicitly where the Radix default differed (RadioItem now needs it;
  CheckboxItem no longer needs `preventDefault`).
- **Focus props**: `onOpenAutoFocus` → `initialFocus` (4 dialogs),
  `onCloseAutoFocus` → `finalFocus` (3 menus).
- **`event.preventDefault()` → `event.preventBaseUIHandler()`** in 2 alert
  dialog actions that must stay open during an async call.
- **Class hooks**: `data-[state=checked]` → `data-checked`,
  `data-[state=active]` → `data-active`, `data-[state=open|closed]` →
  `data-open`/`data-closed`, and every `--radix-*` CSS var to its Base UI name.
- **Structure**: `DropdownMenuLabel` had to move inside `DropdownMenuGroup`
  (Base UI's `GroupLabel` throws outside a Group).

## Tests touched

Seven test files were adjusted, none of them to weaken an assertion:

- Five files: `screen.getByRole("menuitem"…)` → `await screen.findByRole(…)`,
  because Base UI mounts a menu's portal a tick after the trigger click.
- `modal-layout.test.tsx`: asserted Radix's `data-scroll-locked` attribute on
  `<body>`; now asserts the scroll lock itself (`overflow-y: hidden`), which is
  how Base UI locks. The test's real subject — Electron title-bar padding
  staying on `#root` — is unchanged.
- `artifact-panel.test.tsx` needed no change: it caught a real regression (see
  below) and the source was fixed instead.

## Behavior changes shipped (each flagged, none silently patched)

Full detail in the per-component reports; the ones to look at before release:

1. **Tooltips lose `aria-describedby`** (`tooltip.md`). Base UI treats tooltips
   as visual-only. `role="tooltip"` was restored on the popup so existing tests
   and screen-reader identification still work, but the trigger→popup
   description link cannot be restored from the wrapper. Icon-only triggers
   need their own `aria-label`.
2. **Separators are now announced** (`separator.md`). Base UI has no
   `decorative`; every separator renders `role="separator"`.
3. **Scroll-area scrollbars no longer fade on hover** (`scroll-area.md`).
   Radix's `type="hover"` is gone; visibility is CSS-driven now.
4. **Tabs switch to manual keyboard activation** (`tabs.md`). Arrow keys move
   focus; Enter/Space activates.
5. **Context menus lose `modal={false}`** (`context-menu.md`). Base UI omits
   the prop entirely.
6. **Radio items gain their checked fill** (`radio-group.md`). The registry's
   `data-checked:` classes were dead under Radix and now apply.
7. **Alert dialog focus on open** moves from Cancel to the first tabbable
   element (`alert-dialog.md`).

## Divergences from the base-nova registry (deliberate)

- `AlertDialogAction` renders through `AlertDialog.Close`, not a plain
  `<Button>`, so it still closes the dialog — nine call sites depend on that.
- `Button` keeps `data-variant` / `data-size`, which the golden drops and three
  tests assert.
- The artifact download stayed an `<a>` with `buttonVariants()` instead of a
  `Button render={<a/>}`, because Base UI's non-native button mode forces
  `role="button"` over a link.
- `button-group`'s `ButtonGroupText` did not take the golden's new
  `data-slot`, which only makes sense together with the golden's rewritten
  variant classes.

## Repo gotcha

`src/components/ui/combobox.tsx` contains literal NUL bytes (a `"\0"` keyword
separator at lines 351/354). A plain UTF-8 `grep -rn radix src` silently skips
that file. Use `grep -a` or `LC_ALL=C` for any leftover scan here, or a
migration will look finished while a Radix import is still live.

## Not committed

Per `AGENTS.md` ("Do not commit unless asked"), everything is left in the
working tree.
