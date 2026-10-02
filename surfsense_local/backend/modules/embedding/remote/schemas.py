from pydantic import BaseModel, Field

from modules.embedding.spec import Identified


class RemoteEmbedderRead(BaseModel):
    name: str
    identified: Identified
    context: int | None


class RemoteCheckWrite(BaseModel):
    connection_id: int
    model: str = Field(min_length=1, max_length=512)


class RemoteCheckRead(BaseModel):
    # What finishing onboarding sends to lock this model.
    choice: str
    name: str
    identified: Identified
    dimension: int
