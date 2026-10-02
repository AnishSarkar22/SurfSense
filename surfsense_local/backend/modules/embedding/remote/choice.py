"""A server model as onboarding's choice: one string, like a local model's id,
so finishing onboarding takes either. Checked specs wait here for that finish.

Held in memory, by the one API process: a restart between the check and Finish
asks for the check again rather than locking a model nobody checked.
"""

from modules.embedding.spec import EmbedderSpec

PREFIX = "remote:"
_checked: dict[str, EmbedderSpec] = {}


def choice_for(connection_id: int, model: str) -> str:
    # The model id may hold colons itself (Ollama's `name:tag`), so it goes last.
    return f"{PREFIX}{connection_id}:{model}"


def is_remote(choice: str) -> bool:
    return choice.startswith(PREFIX)


def hold(spec: EmbedderSpec) -> None:
    _checked[spec.id] = spec


def checked(choice: str) -> EmbedderSpec | None:
    return _checked.get(choice)
