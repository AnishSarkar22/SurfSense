from __future__ import annotations

from collections.abc import Mapping

import pytest
from pydantic import ValidationError

from app.deliverables.video.contracts import CreativeVideoProject
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


def _project() -> CreativeVideoProject:
    return CreativeVideoProject(
        narration_cues=({"cue_id": "opening", "text": "A concise opening."},),
        source_files=(
            {
                "path": "JobComposition.tsx",
                "source": "export const JobComposition = () => null;",
            },
        ),
        assets=({"id": "logo", "path": "assets/logo.svg", "kind": "svg"},),
    )


def test_provider_schema_is_closed_required_and_constraint_free() -> None:
    schema = provider_json_schema(CreativeVideoProject)

    assert schema["type"] == "object"
    _assert_provider_safe(schema)


def test_creative_project_is_content_only_and_confined() -> None:
    document = _project().model_dump(mode="json")
    assert set(document) == {"narration_cues", "language", "source_files", "assets"}
    assert {
        "beat",
        "beats",
        "layer",
        "layers",
        "scene",
        "transition",
        "command",
        "dependencies",
        "render_settings",
    }.isdisjoint(str(CreativeVideoProject.model_json_schema()).casefold().split())

    document["beats"] = []
    with pytest.raises(ValidationError, match="beats"):
        CreativeVideoProject.model_validate(document)

    for field, value in (
        ("source_files", [{"path": "../escape.tsx", "source": "x"}]),
        (
            "assets",
            [{"id": "logo", "path": "https://example.com/logo.svg", "kind": "svg"}],
        ),
    ):
        invalid = _project().model_dump()
        invalid[field] = value
        with pytest.raises(ValidationError):
            CreativeVideoProject.model_validate(invalid)


def test_creative_project_requires_unique_cues_and_fixed_entrypoint() -> None:
    document = _project().model_dump()
    document["narration_cues"] *= 2
    with pytest.raises(ValidationError, match="cue IDs must be unique"):
        CreativeVideoProject.model_validate(document)

    document = _project().model_dump()
    document["source_files"][0]["path"] = "Other.tsx"
    with pytest.raises(ValidationError, match=r"JobComposition\.tsx"):
        CreativeVideoProject.model_validate(document)
