"""Choosing an embedding model a server runs, and embedding through it.

The servers are one fake that speaks as a plain OpenAI-compatible server,
Ollama, LM Studio, TEI or OpenRouter. The model's own checks are faked at
`verify`, which the unit tests cover; the encoder's call is not.
"""

import hashlib
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest
from httpx import AsyncClient

from modules.embedding.encoder import Purpose, embed
from modules.embedding.remote.endpoint import RemoteEndpoint
from modules.embedding.spec import EmbedderSpec

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

WIDTH = 8
CHAT = {"provider": "llamacpp", "name": "Qwen3-1.7B-Q4_K_M"}


class FakeServer(BaseHTTPRequestHandler):
    """`kind` decides which of the servers' own routes answer."""

    kind = "plain"
    listed: ClassVar[list[str]] = ["text-embedding-3-small", "gpt-4o"]
    embedded: ClassVar[list[dict]] = []

    def do_GET(self) -> None:
        kind, path = self.kind, self.path.split("?")[0]
        if path == "/v1/models" and kind != "tei":
            self._json({"data": [{"id": name} for name in self.listed]})
        elif path == "/v1/embeddings/models" and kind == "openrouter":
            self._json(
                {
                    "data": [
                        {
                            "id": "openai/text-embedding-3-large",
                            "context_length": 8192,
                            "architecture": {"output_modalities": ["embeddings"]},
                        }
                    ]
                }
            )
        elif path == "/api/version" and kind == "ollama":
            self._json({"version": "0.12.0"})
        elif path == "/api/tags" and kind == "ollama":
            self._json({"models": [{"name": n} for n in ("nomic-embed:v1", "llama3")]})
        elif path == "/api/v1/models" and kind == "lmstudio":
            self._json(
                {
                    "models": [
                        {"type": "llm", "key": "qwen3-4b"},
                        {
                            "type": "embedding",
                            "key": "text-embedding-nomic",
                            "max_context_length": 2048,
                        },
                    ]
                }
            )
        elif path == "/info" and kind == "tei":
            self._json(
                {
                    "model_id": "BAAI/bge-base-en-v1.5",
                    "model_type": {"embedding": {"pooling": "cls"}},
                    "max_input_length": 512,
                }
            )
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show" and self.kind == "ollama":
            embeds = body["model"].startswith("nomic")
            self._json({"capabilities": ["embedding"] if embeds else ["completion"]})
        elif self.path == "/v1/embeddings":
            FakeServer.embedded.append(body)
            # Answered out of order, as some servers do; `index` places each.
            data = [
                {"index": i, "embedding": _vector(text)}
                for i, text in enumerate(body["input"])
            ]
            self._json({"data": list(reversed(data))})
        else:
            self.send_error(404)

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Keep the request log out of the test output."""


def _vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [b / 255 for b in digest[:WIDTH]]


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The fake, as a plain server, on a free port; its base URL ends in /v1."""
    monkeypatch.setattr(FakeServer, "kind", "plain")
    monkeypatch.setattr(FakeServer, "embedded", [])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeServer)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1"
    httpd.shutdown()


@pytest.fixture
def checks(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The probe and the search check, answering as told."""
    outcome = {"refusal": None}
    monkeypatch.setattr(
        "modules.embedding.remote.check.verify",
        lambda spec, endpoint: (WIDTH, outcome["refusal"]),
    )
    return outcome


async def _connect(client: AsyncClient, base_url: str) -> int:
    reply = await client.post(
        "/llm/connections",
        json={
            "label": "Home server",
            "provider": "openai_compatible",
            "base_url": base_url,
            "api_key": "secret",
        },
    )
    assert reply.status_code == 201, reply.text
    return reply.json()["id"]


async def _embedders(client: AsyncClient, connection: int) -> dict[str, str]:
    reply = await client.get(f"/embedding/remote/connections/{connection}/models")
    assert reply.status_code == 200, reply.text
    return {model["name"]: model["identified"] for model in reply.json()}


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        # Nothing but the name and the catalog to go on.
        ("plain", {"text-embedding-3-small": "declared"}),
        ("ollama", {"nomic-embed:v1": "declared"}),
        ("lmstudio", {"text-embedding-nomic": "declared"}),
        # No /models at all: the server's own /info is the listing.
        ("tei", {"BAAI/bge-base-en-v1.5": "declared"}),
        ("openrouter", {"openai/text-embedding-3-large": "declared"}),
    ],
)
async def test_each_server_says_which_of_its_models_embed(
    client: AsyncClient, server: str, monkeypatch, kind: str, expected: dict
) -> None:
    """Chat models are left out; what the server declares is believed."""
    monkeypatch.setattr(FakeServer, "kind", kind)
    if kind in ("ollama", "lmstudio", "openrouter"):
        monkeypatch.setattr(FakeServer, "listed", ["llama3", "qwen3-4b"])

    assert await _embedders(client, await _connect(client, server)) == expected


async def test_a_name_alone_is_inferred(
    client: AsyncClient, server: str, monkeypatch
) -> None:
    """No server word and no catalog entry: the name is weaker evidence."""
    monkeypatch.setattr(FakeServer, "listed", ["acme-embed-v2", "acme-chat"])

    found = await _embedders(client, await _connect(client, server))

    assert found == {"acme-embed-v2": "inferred"}


async def test_a_checked_server_model_is_locked_at_onboarding(
    unlocked_client: AsyncClient, server: str, checks, llamacpp_server: str
) -> None:
    """Checked when the user picks it, fixed when the user finishes."""
    client = unlocked_client
    connection = await _connect(client, server)
    checked = await client.post(
        "/embedding/remote/check",
        json={"connection_id": connection, "model": "text-embedding-3-small"},
    )
    assert checked.status_code == 200, checked.text
    choice = checked.json()["choice"]

    await client.put("/llm/selection/text_gen", json=CHAT)
    finished = await client.post("/llm/onboarding", json={"embedding_model": choice})

    assert finished.status_code == 200, finished.text
    active = (await client.get("/embedding/index")).json()["active"]
    assert active["name"] == "text-embedding-3-small"
    assert active["server"] == "Home server"
    spec = active["spec"]
    assert (spec["source"], spec["identified"]) == ("remote", "declared")
    assert (spec["connection_id"], spec["dimension"]) == (connection, WIDTH)


async def test_a_model_that_fails_its_checks_is_refused(
    client: AsyncClient, server: str, checks
) -> None:
    """A chat model served as an embedder ranks decoys first."""
    checks["refusal"] = "It found 6 of 10 answers first."
    connection = await _connect(client, server)

    refused = await client.post(
        "/embedding/remote/check",
        json={"connection_id": connection, "model": "gpt-4o"},
    )

    assert refused.status_code == 422
    assert "6 of 10" in refused.text


async def test_a_typed_model_nothing_vouches_for_is_unverified(
    client: AsyncClient, server: str, checks
) -> None:
    """Named by hand and unknown: allowed once it passes, labelled as such."""
    connection = await _connect(client, server)

    checked = await client.post(
        "/embedding/remote/check",
        json={"connection_id": connection, "model": "team/house-model"},
    )

    assert checked.json()["identified"] == "unverified"


async def test_the_server_the_library_embeds_with_cannot_be_disconnected(
    unlocked_client: AsyncClient, server: str, checks, llamacpp_server: str
) -> None:
    """Every vector came from it; without it nothing more can be embedded."""
    client = unlocked_client
    connection = await _connect(client, server)
    choice = (
        await client.post(
            "/embedding/remote/check",
            json={"connection_id": connection, "model": "text-embedding-3-small"},
        )
    ).json()["choice"]
    await client.put("/llm/selection/text_gen", json=CHAT)
    await client.post("/llm/onboarding", json={"embedding_model": choice})

    refused = await client.delete(f"/llm/connections/{connection}")

    assert refused.status_code == 409
    assert "embedding" in refused.json()["detail"]


async def test_texts_are_embedded_in_order_with_the_connections_key(
    server: str,
) -> None:
    """The encoder's own call: batched, placed by index, normalised."""
    spec = EmbedderSpec(
        id="remote:1:text-embedding-3-small",
        source="remote",
        identified="declared",
        connection_id=1,
        model="text-embedding-3-small",
        dimension=WIDTH,
        pooling="in_model",
        normalize=True,
        max_tokens=8192,
        semantic_weight=0.65,
        batch=2,
    )
    texts = ["alpha", "beta", "gamma"]

    vectors = embed(
        spec, texts, Purpose.DOCUMENT, endpoint=RemoteEndpoint(server, "secret")
    )

    assert [len(body["input"]) for body in FakeServer.embedded] == [2, 1]
    for text, vector in zip(texts, vectors, strict=True):
        expected = _vector(text)
        norm = sum(v * v for v in expected) ** 0.5
        assert vector == pytest.approx([v / norm for v in expected])
