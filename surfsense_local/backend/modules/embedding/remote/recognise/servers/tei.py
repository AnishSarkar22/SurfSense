"""Hugging Face TEI: one model per server, described by `/info`. It has no
`/models`, so this is its listing too."""

import httpx

from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.spec import Identified


async def tei_embedders(
    client: httpx.AsyncClient, root: str
) -> list[Recognised] | None:
    reply = await client.get(f"{root}/info")
    if reply.status_code != 200:
        return None
    try:
        info = reply.json()
    except ValueError:
        return None
    if not isinstance(info, dict) or not isinstance(info.get("model_id"), str):
        return None
    # `classifier` and `reranker` are TEI's other kinds; neither returns a vector.
    model_type = info.get("model_type")
    if not isinstance(model_type, dict) or "embedding" not in model_type:
        return []
    return [
        Recognised(info["model_id"], Identified.DECLARED, info.get("max_input_length"))
    ]
