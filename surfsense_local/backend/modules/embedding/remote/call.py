"""One batch of texts through a server's OpenAI-compatible `/embeddings`."""

import httpx

from modules.embedding.remote.endpoint import RemoteEndpoint
from modules.llm.connections.key_headers import key_headers

TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class RemoteEmbeddingError(Exception):
    """The server did not return a vector for every text, in words to show."""


def embed_remote(
    endpoint: RemoteEndpoint, model: str, texts: list[str]
) -> list[list[float]]:
    try:
        reply = httpx.post(
            f"{endpoint.base_url}/embeddings",
            json={"model": model, "input": texts, "encoding_format": "float"},
            headers=key_headers(endpoint.base_url, endpoint.api_key),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as error:
        raise RemoteEmbeddingError(
            f"could not reach {endpoint.base_url}: {error}"
        ) from error
    if reply.status_code != 200:
        raise RemoteEmbeddingError(
            f"{endpoint.base_url} refused to embed with {model}: "
            f"{reply.status_code} {reply.text[:200]}"
        )
    try:
        data = reply.json()["data"]
        # Placed by `index`, since some servers answer out of order.
        placed = sorted(data, key=lambda item: item["index"])
        vectors = [[float(v) for v in item["embedding"]] for item in placed]
    except (ValueError, KeyError, TypeError) as error:
        raise RemoteEmbeddingError(
            f"{endpoint.base_url} answered without vectors for {model}"
        ) from error
    if len(vectors) != len(texts):
        raise RemoteEmbeddingError(
            f"{endpoint.base_url} returned {len(vectors)} vectors for {len(texts)} texts"
        )
    return vectors
