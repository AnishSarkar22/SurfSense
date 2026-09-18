# avatar

2026-09-18 — golden pair via registry; wrapper was pristine apart from its `cn`
import and the project's extra parts. Migrated; typecheck clean, tests at
baseline parity.

## Changed

- `src/components/ui/avatar.tsx` — import moved to `@base-ui/react/avatar`;
  `Root`/`Image`/`Fallback` parts are unchanged in name. Props types became
  `AvatarPrimitive.Root.Props`, `AvatarPrimitive.Image.Props` and
  `AvatarPrimitive.Fallback.Props`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" avatar.tsx` returns nothing.

## Left alone

- `AvatarBadge`, `AvatarGroup`, `AvatarGroupCount` — project-only parts built
  on plain elements; they never touched Radix.

## Behavior changes

- Radix's `AvatarFallback` supports `delayMs` to avoid a flash before the image
  loads. Base UI's Fallback has no delay prop. No call site used `delayMs`, so
  nothing changed in practice; a fallback may now appear a frame earlier on a
  slow image.

## Verify by hand

1. Open the workspace rail and confirm avatars still render round, at the right
   size for `data-size` sm/default/lg, with the ring and badge positioned as
   before.
