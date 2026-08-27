"""Current model-facing catalog for source-authored sandbox capabilities."""

from __future__ import annotations

from .schema import CapabilityIndex, CapabilityKind, materialize_json


def build_public_capability_catalog(index: CapabilityIndex) -> dict[str, object]:
    """Expose the complete generated public catalog without retrieval-era scoring."""

    capabilities: list[dict[str, object]] = []
    for capability in index.capabilities:
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
            }
        )
    if not capabilities:
        raise ValueError("generated public video capability catalog is empty")
    return {
        "build_id": index.build_id,
        "module": "@surfsense/video/capabilities",
        "capabilities": capabilities,
    }
