# Capability attribution

The implementations under `atoms/` are adapted from the
[Remocn](https://remocn.dev) copy-paste registry and are used under its MIT
license.

| Capability | Upstream source | Reviewed revision |
| --- | --- | --- |
| Animated bar chart | https://remocn.dev/r/animated-bar-chart.json | `registry-2026-08-25` |
| Blur out up | https://remocn.dev/r/blur-out-up.json | `registry-2026-08-25` |
| Whip pan | https://remocn.dev/r/whip-pan.json | `registry-2026-08-25` |

Only offline, deterministic, composable atoms with bounded props and render
fixtures are accepted. Templates, complete compositions, timeline owners,
network-dependent components, and incompatible or unadapted components are
excluded. `slide-swap` and `spring-settle` are explicitly excluded because they
own the timeline.

Each vendored declaration records its upstream documentation and reviewed
revision. The build validates declarations, loaders, dependencies, fixtures,
and exclusions before producing the trusted runtime index.
