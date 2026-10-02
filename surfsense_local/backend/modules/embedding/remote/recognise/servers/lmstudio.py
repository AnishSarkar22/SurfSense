"""LM Studio: its own model list types each model, `"embedding"` in the v1 API
(0.4.0) and `"embeddings"` in v0 before it. v1 names a model by `key`, v0 by
`id`."""

import httpx

from modules.embedding.remote.recognise.recognised import Recognised
from modules.embedding.spec import Identified


async def lmstudio_embedders(
    client: httpx.AsyncClient, root: str
) -> list[Recognised] | None:
    v1 = await client.get(f"{root}/api/v1/models")
    if v1.status_code == 200 and isinstance(_json(v1).get("models"), list):
        return _typed(_json(v1)["models"], "embedding", "key")
    v0 = await client.get(f"{root}/api/v0/models")
    if v0.status_code == 200 and isinstance(_json(v0).get("data"), list):
        return _typed(_json(v0)["data"], "embeddings", "id")
    return None


def _typed(models: list, embedding: str, name_field: str) -> list[Recognised]:
    return [
        Recognised(
            model[name_field], Identified.DECLARED, model.get("max_context_length")
        )
        for model in models
        if isinstance(model, dict)
        and model.get("type") == embedding
        and isinstance(model.get(name_field), str)
    ]


def _json(reply: httpx.Response) -> dict:
    try:
        body = reply.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}
