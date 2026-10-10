"""What a source returned for one call: text for a model, data for the step."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceResult:
    text: str
    structured: dict[str, Any] | None
    # The tool ran and reported failure; the model reads why.
    is_error: bool
