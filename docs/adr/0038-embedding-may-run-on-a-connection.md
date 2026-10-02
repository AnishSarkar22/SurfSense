# ADR 0038: The embedding model may run on a connection, once its checks pass

- **Status:** Accepted
- **Date:** 2026-10-02
- **Source:** [Choosing the embedding model once](../proposals/embedding-model-choice.md)

## Context

[ADR 0015](0015-openai-compatible-connections.md) kept embeddings out of connections, and [ADR 0007](0007-bundled-embeddings.md) left remote embedding as a later opt-in. Onboarding now lets the user choose the library's embedder ([ADR 0036](0036-the-index-records-its-embedder.md)), and some users already pay for a hosted one or run one on their own server. A wrong embedder never fails where the user sees it: it returns vectors, and search ranks badly. And the remote catalog cannot tell an embedder from a chat model, since models.dev records both as `text -> text`.

## Decision

- **Through the same connections** as every other remote model, called at `POST {base_url}/embeddings`. No second kind of connection.
- **Recognised by evidence, in order:** what the server itself declares (Ollama, LM Studio, TEI and OpenRouter each have a route that says so), then the catalog's `family`, then the name. A model typed by hand with none of these is `unverified`.
- **Checked before it is held**, like a Hugging Face pick: the probe sets the width, and the search check must find every answer first.
- **The spec names the connection, never its URL or key**, which are read whenever the index is, so editing them keeps the index.
- **No fallback.** An unreachable server, or a host turned off in Settings › Network, stops ingest, Studio and search with a reason.
- **Rejected: a separate manifest of remote embedders.** The catalog already lists the providers. It cannot classify embedders, but its `family` and `context` are still evidence, and the servers' own routes do the rest.

## Consequences

- The connection the active index uses cannot be deleted.
- A server with no `/models`, such as TEI, can be saved as a connection when it declares embedders of its own.
- Every passage and every question goes to the server's host, in the background, under the consent given in onboarding.
- A model its provider retires cannot be repaired until changing the model is built ([proposal](../proposals/embedding-model-change.md)).
