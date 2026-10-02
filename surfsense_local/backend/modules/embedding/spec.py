"""Everything that decides what a vector means.

An index stores a snapshot of this, so a later edit to a manifest entry cannot
change what an existing index's vectors are.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Source(StrEnum):
    CURATED = "curated"
    HUGGINGFACE = "huggingface"
    REMOTE = "remote"


class Identified(StrEnum):
    """How SurfSense knows the model is built to embed."""

    MEASURED = "measured"
    DECLARED = "declared"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


class Pooling(StrEnum):
    CLS = "cls"
    MEAN = "mean"
    LAST = "last"
    # The build pools inside its own graph and returns one vector per text,
    # as every remote server does.
    IN_MODEL = "in_model"


class PinnedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EmbedderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    source: Source
    identified: Identified
    # A local model's files, pinned; None for a remote one.
    repo: str | None = Field(default=None, min_length=1)
    revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    weights: PinnedFile | None = None
    tokenizer: PinnedFile | None = None
    # A remote model: the connection to call and the id it answers to. The URL
    # and key are read from the connection, so editing them keeps the index.
    connection_id: int | None = None
    model: str | None = Field(default=None, min_length=1)
    dimension: int = Field(gt=0)
    pooling: Pooling
    normalize: bool
    query_prefix: str = ""
    document_prefix: str = ""
    max_tokens: int = Field(gt=0)
    semantic_weight: float = Field(gt=0, lt=1)
    # Passages embedded at once; the batch, not the weights, sets peak memory.
    batch: int = Field(default=32, gt=0)

    @model_validator(mode="after")
    def _one_runtime(self) -> Self:
        local = (self.repo, self.revision, self.weights, self.tokenizer)
        remote = (self.connection_id, self.model)
        if self.source is Source.REMOTE:
            if None in remote or any(v is not None for v in local):
                raise ValueError("a remote spec names a connection and a model only")
        elif None in local or any(v is not None for v in remote):
            raise ValueError("a local spec pins its repo, revision and files only")
        return self
