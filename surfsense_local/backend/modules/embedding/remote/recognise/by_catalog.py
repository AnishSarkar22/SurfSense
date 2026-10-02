"""An embedder by its models.dev entry. Modalities cannot tell: every embedder
there is `text -> text`, like a chat model. Its `family` can, where present."""

from modules.llm.catalog.remote.manifest.loader import remote_lookup
from modules.llm.catalog.remote.manifest.schema import RemoteModel


def catalog_entry(model_id: str, provider: str | None) -> RemoteModel | None:
    return remote_lookup().entry(model_id, provider)


def family_says_embedder(entry: RemoteModel | None) -> bool:
    """`text-embedding`, `cohere-embed`, `mistral-embed`, `titan-embed` and
    `codestral-embed` today; Gemini, Qwen and Voyage embedders carry no such
    family and fall to their name."""
    return entry is not None and "embed" in (entry.family or "")
