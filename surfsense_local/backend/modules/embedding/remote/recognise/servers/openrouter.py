"""OpenRouter lists its embedders apart: `/models` leaves every one out, and
`/embeddings/models` holds them, each with `output_modalities: ["embeddings"]`."""

import httpx

from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.spec import Identified


async def openrouter_embedders(
    client: httpx.AsyncClient, base_url: str
) -> list[Recognised] | None:
    reply = await client.get(f"{base_url}/embeddings/models")
    if reply.status_code != 200:
        return None
    try:
        data = reply.json().get("data")
    except (ValueError, AttributeError):
        return None
    if not isinstance(data, list):
        return None
    return [
        Recognised(entry["id"], Identified.DECLARED, entry.get("context_length"))
        for entry in data
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    ]
