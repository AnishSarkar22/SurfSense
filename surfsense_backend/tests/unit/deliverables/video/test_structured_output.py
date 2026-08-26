from __future__ import annotations

from collections.abc import Mapping

import pytest

from app.deliverables.video.contracts import (
    AuthoredCapabilityLayer,
    AuthoredCapabilityProp,
    AuthoredVideoPlan,
    Bounds,
    CreativeOutline,
    NarrationRewrite,
)
from app.deliverables.video.structured_output import provider_json_schema

pytestmark = pytest.mark.unit

_UNSUPPORTED_KEYWORDS = {
    "default",
    "discriminator",
    "format",
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "multipleOf",
    "oneOf",
    "pattern",
    "uniqueItems",
}


def _assert_provider_safe(value: object) -> None:
    if isinstance(value, Mapping):
        assert _UNSUPPORTED_KEYWORDS.isdisjoint(value)
        properties = value.get("properties")
        if isinstance(properties, Mapping):
            assert value.get("additionalProperties") is False
            assert set(value.get("required", ())) == set(properties)
        for child in value.values():
            _assert_provider_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_provider_safe(child)


@pytest.mark.parametrize(
    "model",
    [CreativeOutline, AuthoredVideoPlan, NarrationRewrite],
)
def test_provider_schema_is_closed_required_and_constraint_free(model) -> None:
    schema = provider_json_schema(model)

    assert schema["type"] == "object"
    _assert_provider_safe(schema)


def test_authored_props_are_closed_and_keep_backend_validation() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        AuthoredCapabilityLayer(
            type="capability",
            id="chart",
            bounds=Bounds(x=0, y=0, width=100, height=100),
            capability_slot="capability-01",
            props=(
                AuthoredCapabilityProp(key="data", value=(1.0, 2.0)),
                AuthoredCapabilityProp(key="data", value=(3.0, 4.0)),
            ),
        )

    with pytest.raises(ValueError):
        AuthoredCapabilityProp(key="", value=True)
