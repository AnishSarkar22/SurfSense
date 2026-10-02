"""Whether a model SurfSense did not measure works, after its download or once
its server is reachable."""

from modules.embedding.encoder import Purpose, embed, width
from modules.embedding.remote.endpoint import RemoteEndpoint
from modules.embedding.search_check import search_check
from modules.embedding.spec import EmbedderSpec

PROBE = "The scanner battery lasts about ten hours on a full charge."


def verify(
    spec: EmbedderSpec, endpoint: RemoteEndpoint | None = None
) -> tuple[int, str | None]:
    """Its real width, and why it is refused, or None. The probe's width wins
    over the config's, which a model with a projection layer gets wrong."""
    probed = spec.model_copy(update={"dimension": width(spec, PROBE, endpoint)})
    result = search_check(
        lambda texts: embed(probed, texts, Purpose.QUERY, endpoint=endpoint),
        lambda texts: embed(probed, texts, Purpose.DOCUMENT, endpoint=endpoint),
    )
    if not result.passed:
        return probed.dimension, (
            f"It found {result.first} of {result.asked} answers first; a search "
            f"model has to find all {result.asked}."
        )
    return probed.dimension, None
