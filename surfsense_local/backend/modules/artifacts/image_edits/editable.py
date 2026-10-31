"""Which versions the Edit box may change: a ready picture Studio drew or edited."""

from modules.artifacts.models import Artifact, ArtifactFileRole
from modules.documents.models import DocumentStatus

EDITABLE_FORMATS = frozenset({"image", "infographic"})


def has_picture(artifact: Artifact) -> bool:
    return artifact.format in EDITABLE_FORMATS and any(
        file.role is ArtifactFileRole.PRIMARY for file in artifact.files
    )


def image_editable(artifact: Artifact) -> bool:
    return artifact.document.status is DocumentStatus.READY and has_picture(artifact)
