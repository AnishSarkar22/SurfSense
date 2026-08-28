# Capability attribution

The implementations under `atoms/` are adapted from the
[Remocn](https://remocn.dev) copy-paste registry and are used under its MIT
license.

| Capability | Upstream source | Reviewed revision |
| --- | --- | --- |
| Animated bar chart | https://remocn.dev/r/animated-bar-chart.json | `registry-2026-08-25` |
| Animated line chart | https://remocn.dev/r/animated-line-chart.json | `registry-fetched-2026-08-28` |
| Backdrop | https://remocn.dev/r/backdrop.json | `registry-fetched-2026-08-28` |
| Blur out up | https://remocn.dev/r/blur-out-up.json | `registry-2026-08-25` |
| Drift | https://remocn.dev/r/drift.json | `registry-fetched-2026-08-28` |
| Focus blur resolve | https://remocn.dev/r/focus-blur-resolve.json | `registry-fetched-2026-08-28` |
| Mask reveal up | https://remocn.dev/r/mask-reveal-up.json | `registry-fetched-2026-08-28` |
| Micro scale fade | https://remocn.dev/r/micro-scale-fade.json | `registry-fetched-2026-08-28` |
| Per character rise | https://remocn.dev/r/per-character-rise.json | `registry-fetched-2026-08-28` |
| Scale down fade | https://remocn.dev/r/scale-down-fade.json | `registry-fetched-2026-08-28` |
| Staggered fade up | https://remocn.dev/r/staggered-fade-up.json | `registry-fetched-2026-08-28` |
| Tracking in | https://remocn.dev/r/tracking-in.json | `registry-fetched-2026-08-28` |
| Whip pan | https://remocn.dev/r/whip-pan.json | `registry-2026-08-25` |

Only offline, deterministic, composable atoms with bounded props and render
fixtures are accepted. Templates, complete compositions, timeline owners,
network-dependent components, and incompatible or unadapted components are
excluded. `slide-swap` and `spring-settle` are explicitly excluded because they
own the timeline.

Each vendored declaration records its upstream documentation and reviewed
revision. The build validates declarations, loaders, dependencies, fixtures,
and exclusions before producing the trusted runtime index.
