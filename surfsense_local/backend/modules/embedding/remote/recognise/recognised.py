from dataclasses import dataclass

from modules.embedding.spec import Identified


@dataclass(frozen=True)
class Recognised:
    """A model on a server, and how SurfSense knows it embeds."""

    name: str
    identified: Identified
    # The longest passage it accepts, where anything says.
    context: int | None = None
