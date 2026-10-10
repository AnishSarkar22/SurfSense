"""A progress report a server sends while one of its calls runs."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Progress:
    progress: float
    total: float | None
    message: str | None

    @classmethod
    def from_notification(cls, params: dict[str, Any]) -> "Progress":
        return cls(
            progress=params["progress"],
            total=params.get("total"),
            message=params.get("message"),
        )


OnProgress = Callable[[Progress], None]
