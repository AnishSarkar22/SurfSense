# Embedding model

Which model turns passages and questions into vectors. It is chosen once, in onboarding, and fixed for the whole library: every vector in it was made by that model, and changing it means embedding everything again, which is not built ([proposal](../proposals/embedding-model-change.md)).

**Code:** [`modules/embedding/`](../../surfsense_local/backend/modules/embedding/), [`modules/embedding/remote/`](../../surfsense_local/backend/modules/embedding/remote/), [`engines/onnxruntime/`](../../surfsense_local/backend/modules/llm/catalog/local/engines/onnxruntime/), [`frontend/src/features/onboarding/model-step/use-embedding-step.ts`](../../surfsense_local/frontend/src/features/onboarding/model-step/kinds/use-embedding-step.ts), [`frontend/src/features/embedding/`](../../surfsense_local/frontend/src/features/embedding/)
**Decisions:** [ADR 0007](../adr/0007-bundled-embeddings.md), [ADR 0036](../adr/0036-the-index-records-its-embedder.md), [ADR 0037](../adr/0037-embedding-is-a-type-not-a-slot.md), [ADR 0038](../adr/0038-embedding-may-run-on-a-connection.md)

## The index

A row in `embedding_indexes` holds a snapshot of the model's spec and names its vector table ([data model](data-model.md)). Ingest and Studio write through it, search reads through it, and each document records which index it was embedded into ([documents](documents.md), [search](search.md)). Until onboarding finishes there is no row, and the routes that queue embedding work answer `409 embedding_not_chosen`.

## Choosing

Onboarding's last step lists the choices; finishing onboarding locks the one chosen ([selection](local-models/selection.md#onboarding)), and skipping means bge-small. Settings › Embedding shows it, its vector size, and whether SurfSense tested it, and offers no way to change it.

| Source | Where it comes from | Label |
|---|---|---|
| bge-small | bundled in the read-only models pack, pinned by hash | measured |
| curated | the local manifest, run by onnxruntime ([catalog](local-models/catalog.md)); ranking weight measured by the retrieval eval | measured |
| Hugging Face | any ONNX embedder, found by search | declared, or inferred |
| a server | an embedding model on a connection ([connections](connections.md)), called at `POST {base_url}/embeddings` | declared, inferred, or unverified |

## Hugging Face

`GET /embedding/huggingface/search?q=` lists repos tagged `sentence-similarity` or `feature-extraction`, most downloaded first. `GET /embedding/huggingface/repo/{repo}` opens one, without downloading weights, as a catalog row with one build, or none and why. Both answer in the GGUF search's shapes (`SearchRead`, `RepoRead`), so onboarding renders them through the same search as the chat step:

- **Checksums:** a small file Hugging Face keeps out of LFS, such as most `tokenizer.json` files, lists no sha256, so it is hashed from its bytes at the pinned commit.
- **Refused** when gated, when Hugging Face's own security scan flags a file it would take or anything as `unsafe`, when it has no ONNX build or no `tokenizer.json`, or when a weights file lists no checksum.
- **Which file:** a generic int8 build (`model_int8.onnx`, `model_quantized.onnx`), else full precision; never one tuned for a single CPU, an `O1`–`O4` variant, or an fp16, q4 or bnb4 build. External data downloads with it under its own name ([`pick.py`](../../surfsense_local/backend/modules/embedding/huggingface/pick.py)).
- **The spec** comes from the repo's sentence-transformers files: pooling, prompts for questions and passages, maximum length, capped at 2,048 tokens. Vectors are always normalised, since search compares by cosine. A repo with those files is `declared`; one with only the tag is `inferred` and takes bge's defaults. The ranking weight is 0.65, bge's, since nobody measured it ([`spec_from_repo.py`](../../surfsense_local/backend/modules/embedding/huggingface/spec_from_repo.py)).

An open repo is installed through the same install jobs as every local model, under the name `hf--<owner>--<name>`. After the download, two checks run before it can be chosen ([`verify.py`](../../surfsense_local/backend/modules/embedding/verify.py)):

1. **The probe** embeds one passage; its width is the one kept, over whatever the config said.
2. **The search check** asks ten questions over twenty passages, each answer beside a decoy on the same topic, and every answer must rank first ([`search_check.py`](../../surfsense_local/backend/modules/embedding/search_check.py)). bge-small and both curated granite models found 10 of 10; chat models served as embedders found 5 to 8, except one at 10. It shows a model can find answers, not that it was built to embed.

A model that fails is deleted and the install says why. One that passes keeps its settled spec beside its files and is listed as a downloaded row, labelled not tested by SurfSense.

## A server's model

The embedding step offers the same "Use a server" path as the other steps, with the same per-server list, but its listing and its Use are its own ([`modules/embedding/remote/`](../../surfsense_local/backend/modules/embedding/remote/)).

`GET /embedding/remote/connections/{id}/models` lists the models that embed. Modalities cannot tell: models.dev records every embedder as `text -> text`, like a chat model. So the first source that answers decides ([`listing.py`](../../surfsense_local/backend/modules/embedding/remote/recognise/listing.py)):

1. **The server says so** (`declared`). Each adapter asks its own route and answers nothing on a server of another kind:
   - TEI's `/info` has a `model_type` of `embedding`, and is TEI's listing too, since TEI has no `/models`.
   - Ollama's `/api/show` lists `embedding` among a model's capabilities.
   - LM Studio's `/api/v1/models` types a model `embedding`, or `/api/v0/models` types it `embeddings`.
   - OpenRouter's `{base_url}/embeddings/models` lists the embedders its `/models` leaves out.
2. **The catalog's `family`** names an embedder (`declared`): `text-embedding`, `cohere-embed`, `mistral-embed`, `titan-embed`, `codestral-embed`.
3. **The name** carries an embedder term (`inferred`), the terms chat uses to refuse embedders, less `rerank`.

A model none of these vouches for is left out of the list. Typed by hand as an exact ID, it is `unverified`. llama-server and vLLM say nothing of their own, and Ollama, llama-server and vLLM return vectors even from a chat model, so the checks below decide for them.

`POST /embedding/remote/check` runs the same two checks as a Hugging Face pick, through the server: the probe, which sets the width, and the search check. A model that fails is refused with the reason, and the step keeps its previous choice. One that passes is held in the API's memory under a choice id, `remote:<connection_id>:<model>`, which Finish sends like a local model's id. A restart between the check and Finish asks for the check again. The spec names the connection and the model, never its URL or key: those are read from the connection whenever the active index is, so editing them keeps the index. Vectors are normalised whatever the server returns, and the ranking weight is 0.65 because nobody measured it.

Ingest, Studio and search read the connection through `require_active_index()`, which also checks egress to its host. A host turned off in Settings › Network stops all three with `403 egress_disabled`. An unreachable server stops them with `503 embedding_server_unavailable`, and a document that fails says why. Nothing falls back to another model. The connection the active index uses cannot be deleted (`409`), and editing its key or URL stays allowed.

## Known gaps

- A Hugging Face repo deleted or made private after it was chosen cannot be downloaded again, and a server's model its provider retires cannot be called again. Nothing can repair the library until changing the model is built.
- A provider's own switch for embedding queries and passages differently is not used: questions and passages go to `/embeddings` the same way.
- No warning comes before a provider retires a model, though OpenRouter publishes an `expiration_date` and models.dev a `deprecated` status.
- Onboarding does not say that every document added, and every question, is sent to the server's host.
- A model whose context is shorter than a chunk is not refused in advance; the provider's error fails the document.
