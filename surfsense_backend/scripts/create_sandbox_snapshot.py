"""Register the published sandbox image as the Daytona snapshot.

Both providers run the same image, built from docker/sandbox/Dockerfile and
pushed by CI. OpenSandbox pulls it onto the host docker daemon; Daytona pulls
it into a snapshot, which is what this script creates.

Run from the backend directory:
    cd surfsense_backend
    uv run python scripts/create_sandbox_snapshot.py ghcr.io/modsetter/surfsense-sandbox:<version>

The argument may be omitted when SANDBOX_IMAGE names a pinned tag.

Prerequisites:
    - DAYTONA_API_KEY set in surfsense_backend/.env (or exported in shell)
    - DAYTONA_API_URL=https://app.daytona.io/api
    - DAYTONA_TARGET=us  (or eu)
    - the image is public, or its registry is registered in the Daytona dashboard

The script creates immutable default and video snapshots and prints the two
environment pointers to deploy.
"""

import os
import re
import sys
from pathlib import Path

from daytona import CreateSnapshotParams, Daytona, Resources
from daytona.common.errors import DaytonaNotFoundError
from dotenv import load_dotenv

_here = Path(__file__).parent
for candidate in [
    _here / "../surfsense_backend/.env",
    _here / ".env",
    _here / "../.env",
]:
    if candidate.exists():
        load_dotenv(candidate)
        break

# The image unpacks well past the 3 GiB Daytona's smallest default allows.
DISK_GIB = 10

# Daytona resolves the reference once, at snapshot creation, and never re-pulls
# it, so a moving tag would freeze whatever it happened to see first. Daytona
# rejects these outright rather than let that happen quietly.
UNPINNED_TAGS = frozenset({"latest", "lts", "stable"})


def resolve_image(argv: list[str], environ: dict[str, str]) -> str:
    """Validate the image reference to snapshot, from argv or SANDBOX_IMAGE."""
    image = (argv[1] if len(argv) > 1 else environ.get("SANDBOX_IMAGE", "")).strip()
    if not image:
        raise SystemExit(
            "ERROR: pass the sandbox image, or set SANDBOX_IMAGE to a pinned tag."
        )
    # Only the last path segment can carry the tag; a registry host may hold a
    # colon of its own for a port.
    name = image.rpartition("/")[2]
    if "@" in name:
        return image
    _, separator, tag = name.partition(":")
    if not separator:
        raise SystemExit(
            f"ERROR: {image} has no tag. Daytona requires a tag or digest."
        )
    if tag in UNPINNED_TAGS:
        raise SystemExit(
            f"ERROR: Daytona rejects the '{tag}' tag. Pass a release version instead."
        )
    return image


def snapshot_names(image: str) -> tuple[str, str]:
    """Return immutable profile snapshot names derived from the image version."""
    image_name = image.rpartition("/")[2]
    if "@" in image_name:
        version = image_name.partition("@")[2].removeprefix("sha256:")[:12]
    else:
        version = image_name.partition(":")[2]
    version = re.sub(r"[^a-zA-Z0-9-]+", "-", version).strip("-").lower()
    if not version:
        raise ValueError("Could not derive a snapshot version from the image")
    return (
        f"surfsense-sandbox-{version}",
        f"surfsense-sandbox-video-{version}",
    )


def _positive_int(environ: dict[str, str], name: str, default: int) -> int:
    value = int(environ.get(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def snapshot_params(
    image: str, environ: dict[str, str]
) -> tuple[CreateSnapshotParams, CreateSnapshotParams]:
    """Build resource-pinned default and video snapshot declarations."""
    default_name, video_name = snapshot_names(image)
    common = {
        "image": image,
        # Daytona injects its own daemon and needs only a live container.
        "entrypoint": ["sleep", "infinity"],
    }
    return (
        CreateSnapshotParams(
            name=default_name,
            resources=Resources(
                cpu=_positive_int(environ, "SANDBOX_DEFAULT_CPU", 1),
                memory=_positive_int(environ, "SANDBOX_DEFAULT_MEMORY_GIB", 2),
                disk=DISK_GIB,
            ),
            **common,
        ),
        CreateSnapshotParams(
            name=video_name,
            resources=Resources(
                cpu=_positive_int(environ, "VIDEO_SANDBOX_CPU", 4),
                memory=_positive_int(environ, "VIDEO_SANDBOX_MEMORY_GIB", 8),
                disk=DISK_GIB,
            ),
            **common,
        ),
    )


def _create_if_absent(daytona: Daytona, params: CreateSnapshotParams) -> None:
    try:
        daytona.snapshot.get(params.name)
    except DaytonaNotFoundError:
        print(f"Building snapshot '{params.name}' from {params.image} …\n")
        daytona.snapshot.create(
            params,
            on_logs=lambda chunk: print(chunk, end="", flush=True),
        )
        print(f"\nSnapshot '{params.name}' is ready.")
    else:
        print(f"Snapshot '{params.name}' already exists; leaving it unchanged.")


def main() -> None:
    image = resolve_image(sys.argv, os.environ)

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print("ERROR: DAYTONA_API_KEY is not set.", file=sys.stderr)
        print(
            "Add it to surfsense_backend/.env or export it in your shell.",
            file=sys.stderr,
        )
        sys.exit(1)

    daytona = Daytona()
    default_params, video_params = snapshot_params(image, os.environ)
    _create_if_absent(daytona, default_params)
    _create_if_absent(daytona, video_params)
    print("\nAdd this to surfsense_backend/.env:")
    print(f"    DAYTONA_SNAPSHOT_ID={default_params.name}")
    print(f"    DAYTONA_VIDEO_SNAPSHOT_ID={video_params.name}")


if __name__ == "__main__":
    main()
