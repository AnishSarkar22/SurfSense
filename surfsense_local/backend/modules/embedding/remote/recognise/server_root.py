from urllib.parse import urlsplit, urlunsplit


def server_root(base_url: str) -> str:
    """The server behind an OpenAI-compatible base URL: Ollama's, LM Studio's
    and TEI's own routes sit at its root, not under `/v1`."""
    parts = urlsplit(base_url)
    path = parts.path.removesuffix("/")
    if path.endswith("/v1"):
        path = path[: -len("/v1")]
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))
