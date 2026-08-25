"""Final selection checks against the exact bounded disclosure."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from jsonschema.validators import validator_for

from .schema import (
    CapabilityDisclosure,
    CapabilityIndex,
    CapabilityKind,
    materialize_json,
)


def validate_selected_capability_ids(
    selected_ids: Iterable[str],
    disclosure: CapabilityDisclosure,
    *,
    build_id: str | None = None,
) -> tuple[str, ...]:
    """Reject model-selected IDs that were not disclosed for this attempt."""

    if build_id is not None and build_id != disclosure.build_id:
        raise ValueError(
            f"capability build mismatch: plan uses {build_id!r}, "
            f"disclosure uses {disclosure.build_id!r}"
        )
    allowed = set(disclosure.disclosed_ids)
    ordered_unique: list[str] = []
    seen: set[str] = set()
    for capability_id in selected_ids:
        if capability_id not in allowed:
            raise ValueError(
                f"selected capability was not disclosed: {capability_id!r}"
            )
        if capability_id not in seen:
            ordered_unique.append(capability_id)
            seen.add(capability_id)
    if not ordered_unique:
        raise ValueError("at least one disclosed capability must be selected")
    return tuple(ordered_unique)


def validate_capability_props(
    index: CapabilityIndex,
    usages: Iterable[tuple[str, CapabilityKind, Mapping[str, Any]]],
) -> None:
    """Validate model-authored props against the live sandbox JSON Schemas."""

    by_id = index.by_id()
    validators: dict[str, Any] = {}
    for capability_id, expected_kind, props in usages:
        capability = by_id.get(capability_id)
        if capability is None or capability.kind is not expected_kind:
            raise ValueError(
                f"{capability_id!r} is not a {expected_kind.value} capability"
            )
        if capability.props_schema is None:
            raise ValueError(f"{capability_id!r} does not admit authored props")
        validator = validators.get(capability_id)
        if validator is None:
            schema = materialize_json(capability.props_schema)
            validator_class = validator_for(schema, default=Draft202012Validator)
            validator_class.check_schema(schema)
            validator = validator_class(schema)
            validators[capability_id] = validator
        error = best_match(validator.iter_errors(dict(props)))
        if error is not None:
            raise ValueError(
                f"invalid props for {capability_id!r} at {error.json_path}: "
                f"{error.message}"
            )
