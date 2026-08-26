"""Provider-enforced structured output for the queued-video authoring path."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "contains",
        "default",
        "discriminator",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "maxContains",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minContains",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "oneOf",
        "pattern",
        "patternProperties",
        "propertyNames",
        "unevaluatedItems",
        "unevaluatedProperties",
        "uniqueItems",
    }
)


def _provider_safe(value: Any) -> Any:
    if isinstance(value, list):
        return [_provider_safe(item) for item in value]
    if not isinstance(value, dict):
        return value

    result = {
        key: _provider_safe(child)
        for key, child in value.items()
        if key not in _UNSUPPORTED_SCHEMA_KEYWORDS and key != "const"
    }
    if "const" in value:
        result["enum"] = [value["const"]]
    if "oneOf" in value:
        result["anyOf"] = _provider_safe(value["oneOf"])

    properties = result.get("properties")
    if isinstance(properties, dict):
        result["required"] = list(properties)
        result["additionalProperties"] = False
    return result


def provider_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return the strict JSON-Schema subset accepted by Azure/OpenAI models."""

    return _provider_safe(model.model_json_schema())


__all__ = ["provider_json_schema"]
