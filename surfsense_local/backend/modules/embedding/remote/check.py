"""A server model put through the same checks as a Hugging Face pick: the
probe, which sets its width, and the search check."""

import asyncio

from modules.embedding.remote.choice import choice_for, hold
from modules.embedding.remote.endpoint import RemoteEndpoint
from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.spec import EmbedderSpec, Pooling, Source
from modules.embedding.verify import verify
from modules.llm.models import ProviderConnection

# bge's, since nobody measured the blend for a server's model.
UNMEASURED_WEIGHT = 0.65
# Where nothing says how long a passage may be: chunks are ~480 tokens.
DEFAULT_MAX_TOKENS = 8192


class RefusedEmbedderError(Exception):
    """It failed its checks, in words the screen shows."""


async def check(connection: ProviderConnection, found: Recognised) -> EmbedderSpec:
    unchecked = EmbedderSpec(
        id=choice_for(connection.id, found.name),
        source=Source.REMOTE,
        identified=found.identified,
        connection_id=connection.id,
        model=found.name,
        # Placeholder: the probe's width replaces it.
        dimension=1,
        pooling=Pooling.IN_MODEL,
        normalize=True,
        max_tokens=found.context or DEFAULT_MAX_TOKENS,
        semantic_weight=UNMEASURED_WEIGHT,
    )
    endpoint = RemoteEndpoint(connection.base_url, connection.api_key)
    width, refusal = await asyncio.to_thread(verify, unchecked, endpoint)
    if refusal is not None:
        raise RefusedEmbedderError(refusal)
    spec = unchecked.model_copy(update={"dimension": width})
    hold(spec)
    return spec
