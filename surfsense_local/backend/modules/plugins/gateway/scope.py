"""Where a call happens: its workspace, its thread, and the turn's message when known."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    workspace_id: int
    thread_id: int | None
    message_id: int | None
