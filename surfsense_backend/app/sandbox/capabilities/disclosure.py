"""Current model-facing catalog for source-authored sandbox capabilities."""

from __future__ import annotations

from .schema import CapabilityId, CapabilityIndex, CapabilityKind, materialize_json


def build_public_capability_catalog(
    index: CapabilityIndex,
    *,
    selected_ids: tuple[CapabilityId, ...],
) -> dict[str, object]:
    """Materialize only the deterministic shortlist's model-facing declarations."""

    capabilities: list[dict[str, object]] = []
    by_id = index.by_id()
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected capability IDs must be unique")
    unknown = set(selected_ids) - set(by_id)
    if unknown:
        raise ValueError(f"selected capability IDs are unknown: {sorted(unknown)}")
    for capability_id in selected_ids:
        capability = by_id[capability_id]
        if capability.kind is CapabilityKind.RENDERER:
            continue
        export_name = capability.declaration.get("public_export")
        if capability.kind in {
            CapabilityKind.COMPONENT,
            CapabilityKind.TRANSITION,
        }:
            if not isinstance(export_name, str) or not export_name:
                raise ValueError(
                    f"public capability {capability.id!r} lacks a public export"
                )
        else:
            export_name = None
        capabilities.append(
            {
                "id": capability.id,
                "kind": capability.kind.value,
                "export_name": export_name,
                "category": capability.category,
                "summary": capability.summary,
                "tags": list(capability.tags),
                "vibe": list(capability.vibe),
                "use_for": list(capability.use_for),
                "avoid_for": list(capability.avoid_for),
                "natural_frame_length": capability.natural_frame_length,
                "dependencies": list(capability.dependencies),
                "native_canvas": (
                    capability.native_canvas.model_dump(mode="json")
                    if capability.native_canvas is not None
                    else None
                ),
                "props_schema": materialize_json(capability.props_schema),
                "example_props": materialize_json(
                    capability.deterministic_test_props
                ),
            }
        )
    if not capabilities:
        raise ValueError("generated public video capability catalog is empty")
    return {
        "build_id": index.build_id,
        "module": "@surfsense/video/capabilities",
        "capabilities": capabilities,
    }
