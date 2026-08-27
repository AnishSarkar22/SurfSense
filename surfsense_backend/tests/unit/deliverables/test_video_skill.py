import pytest

from app.deliverables.video.skill import load_video_skill
from tests.utils.fake_sandbox import FakeSandboxSession


def _session(
    root: str,
    *,
    contract: bytes = b"export type NarrationCueState = { cueId: string };",
    **supplements: str,
) -> FakeSandboxSession:
    files = {
        "/opt/skills/video/SKILL.md": root.encode(),
        "/opt/surfsense/video-runtime/src/authoring-contract.ts": contract,
    }
    files.update(
        {
            f"/opt/skills/video/supplements/{name}.md": value.encode()
            for name, value in supplements.items()
        }
    )
    return FakeSandboxSession(files)


async def test_load_video_skill_reads_only_declared_supplements() -> None:
    root = """---
name: video
supplement_allowlist:
  - supplements/narrative.md
  - supplements/review.md
---
# Video
"""
    loaded = await load_video_skill(
        _session(root, narrative="# Narrative", review="# Review", ignored="# Ignore")
    )

    assert "# Narrative" in loaded.content
    assert "# Review" in loaded.content
    assert "# Ignore" not in loaded.content
    assert loaded.authoring_contract == (
        "export type NarrationCueState = { cueId: string };"
    )


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/other.md",
        "../other.md",
        "supplements/not-markdown.txt",
    ],
)
async def test_load_video_skill_rejects_unsafe_supplement_paths(path: str) -> None:
    root = f"""---
name: video
supplement_allowlist:
  - {path}
---
# Video
"""

    with pytest.raises(ValueError, match="unsafe"):
        await load_video_skill(_session(root))
