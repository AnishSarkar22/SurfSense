# scroll-area

2026-09-18 — golden pair via registry; wrapper was pristine apart from its `cn`
import. Migrated; typecheck clean, tests at baseline parity.

## Changed

- `src/components/ui/scroll-area.tsx` — import moved to
  `@base-ui/react/scroll-area`; `ScrollAreaPrimitive.ScrollAreaScrollbar` →
  `.Scrollbar` and `ScrollAreaPrimitive.ScrollAreaThumb` → `.Thumb`. Root,
  Viewport and Corner keep their names. Props types became
  `ScrollAreaPrimitive.Root.Props` and `ScrollAreaPrimitive.Scrollbar.Props`.

Leftover scan clean: `grep -a "radix-ui\|@radix-ui" scroll-area.tsx` returns
nothing.

## Left alone

- Base UI adds a `ScrollArea.Content` part (a div inside Viewport that makes
  horizontal-overflow measurement exact). The base-nova golden does not use it
  and this app only scrolls vertically (`workspace-rail.tsx:164` is the single
  consumer), so it was not introduced.
- `scroll-shadow.tsx` is a separate project component built on plain scroll
  events; it is not Radix and was not touched.

## Behavior changes

- Scrollbar visibility is no longer prop-driven. Radix's `type` defaulted to
  `"hover"`, so the bar faded in on hover and out after `scrollHideDelay`. Base
  UI dropped both props and expects CSS: style the Scrollbar against
  `[data-hovering]` / `[data-scrolling]`. With the current classes the scrollbar
  simply mounts whenever the viewport overflows, so it reads as always-visible.
  Flagged, not patched — restoring the fade is a class change on
  `ScrollBar`, and it is a deliberate design call.
- `Scrollbar [data-state="visible"|"hidden"]` is gone; `data-hovering`,
  `data-scrolling` and `data-has-overflow-y` replace it.

## Verify by hand

1. Open the workspace rail with enough workspaces to overflow and watch the
   scrollbar: it will now sit there permanently instead of fading in on hover.
   Decide whether that is acceptable before release.
2. Drag the thumb and confirm the rail scrolls; check the horizontal/vertical
   sizing classes still apply (they key off `data-orientation`).
