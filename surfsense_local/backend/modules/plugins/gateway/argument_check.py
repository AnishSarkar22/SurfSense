"""Arguments checked against the tool's input schema before anything is sent."""

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


def argument_problem(schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    """A sentence naming what is wrong, or None when the arguments fit."""
    try:
        validator = Draft202012Validator(schema)
        error = next(iter(validator.iter_errors(arguments)), None)
    except SchemaError:
        # A server's broken schema is not the model's fault: let the server judge.
        return None
    if error is None:
        return None
    where = "/".join(str(part) for part in error.absolute_path) or "the arguments"
    return f"{where}: {error.message}"
