"""How a call ended, as its caller gets it: a refusal is a sentence, never an exception."""

from dataclasses import dataclass
from typing import Any

from modules.plugins.results.models import PluginCallStatus


@dataclass(frozen=True)
class ToolOutcome:
    status: PluginCallStatus
    # For a model: the result, trimmed; or, when refused or failed, why, in a sentence.
    text: str
    structured: dict[str, Any] | None = None
    # None when the call was refused before it was recorded.
    call_id: int | None = None
