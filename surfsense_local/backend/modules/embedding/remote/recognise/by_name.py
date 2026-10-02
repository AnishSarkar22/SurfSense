"""An embedder by its name alone: the weakest evidence, so `inferred`.

The terms chat already uses to refuse embedders (`not_text_gen.py`), less
`rerank`: a reranker scores pairs and returns no vector.
"""

_EMBEDDER_TERMS = (
    "embed",
    "voyage",
    "bge",
    "gte-",
    "e5-",
    "mini-lm",
    "mini_lm",
    "mpnet",
)


def named_like_an_embedder(model_id: str) -> bool:
    name = model_id.lower()
    return "rerank" not in name and any(term in name for term in _EMBEDDER_TERMS)
