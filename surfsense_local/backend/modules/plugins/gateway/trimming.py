"""A result trimmed for a model: its start and end kept, the middle cut, the cut said."""

# Pi trims at the same size: enough for a page of results, small enough for a 32k window.
MODEL_LIMIT_BYTES = 20_000
# Room for the marker itself.
MARKER_ROOM = 100


def trimmed_for_model(text: str) -> str:
    if len(text.encode()) <= MODEL_LIMIT_BYTES:
        return text
    keep = (MODEL_LIMIT_BYTES - MARKER_ROOM) // 2
    head = text.encode()[:keep].decode(errors="ignore")
    tail = text.encode()[-keep:].decode(errors="ignore")
    cut = len(text) - len(head) - len(tail)
    return f"{head}\n\n[… {cut} characters cut from the middle …]\n\n{tail}"
