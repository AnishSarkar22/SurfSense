from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from daytona import Daytona, SandboxState
from daytona.common.errors import DaytonaError

from app.config import config as app_config
from app.sandbox.protocol import SandboxResourceProfile
from app.sandbox.providers.daytona import (
    PROFILE_LABEL_KEY,
    THREAD_LABEL_KEY,
    DaytonaProvider,
    DaytonaSession,
)


async def test_daytona_session_maps_command_and_binary_file_operations():
    sandbox = SimpleNamespace(
        id="daytona-1",
        process=SimpleNamespace(
            exec=Mock(return_value=SimpleNamespace(result="ok", exit_code=0))
        ),
        fs=SimpleNamespace(
            download_file=Mock(return_value=b"\x00binary"),
            upload_file=Mock(),
        ),
    )
    client = SimpleNamespace(delete=Mock())
    session = DaytonaSession(sandbox, client)

    result = await session.execute("print('ok')")
    downloaded = await session.read_file("/workspace/file.bin")
    await session.write_file("/workspace/file.bin", b"new")
    await session.terminate()

    assert result.ok
    assert result.output == "ok"
    wrapped = sandbox.process.exec.call_args.args[0]
    assert "code-interpreter-env.sh" in wrapped
    assert "python3 <<" in wrapped
    assert (
        sandbox.process.exec.call_args.kwargs["timeout"]
        == app_config.SANDBOX_OPERATION_TIMEOUT_SECONDS
    )
    assert downloaded == b"\x00binary"
    sandbox.fs.upload_file.assert_called_once_with(b"new", "/workspace/file.bin")
    client.delete.assert_called_once_with(sandbox)


async def test_keep_alive_resets_daytona_inactivity_timer():
    sandbox = SimpleNamespace(
        id="daytona-1",
        process=SimpleNamespace(
            exec=Mock(return_value=SimpleNamespace(result="", exit_code=0))
        ),
    )
    session = DaytonaSession(sandbox, SimpleNamespace(delete=Mock()))

    await session.keep_alive()

    sandbox.process.exec.assert_called_once_with(
        "true",
        timeout=app_config.SANDBOX_OPERATION_TIMEOUT_SECONDS,
    )


async def test_read_file_maps_missing_file_to_file_not_found():
    """A FILE_NOT_FOUND body must surface as FileNotFoundError, not DaytonaError.

    read_receipt only catches FileNotFoundError; a raw DaytonaError escapes and
    crashes the stream on the first (receiptless) verification.
    """
    missing = DaytonaError(
        'Failed to download file: {"code":"FILE_NOT_FOUND","statusCode":404}'
    )
    sandbox = SimpleNamespace(
        id="daytona-1",
        fs=SimpleNamespace(download_file=Mock(side_effect=missing)),
    )
    session = DaytonaSession(sandbox, SimpleNamespace(delete=Mock()))

    with pytest.raises(FileNotFoundError):
        await session.read_file("/tmp/receipt.json")


async def test_read_file_propagates_non_not_found_errors():
    sandbox = SimpleNamespace(
        id="daytona-1",
        fs=SimpleNamespace(download_file=Mock(side_effect=DaytonaError("boom"))),
    )
    session = DaytonaSession(sandbox, SimpleNamespace(delete=Mock()))

    with pytest.raises(DaytonaError):
        await session.read_file("/tmp/receipt.json")


def _client(items: list[object]) -> Mock:
    """A client mock that only answers calls the real SDK class defines.

    ``spec=Daytona`` is the point of these tests: the provider once called a
    ``find_one`` the SDK had dropped, and stubs without a spec happily
    answered it.
    """
    client = Mock(spec=Daytona)
    client.list.return_value = SimpleNamespace(items=items)
    return client


def _provider(client: Mock) -> DaytonaProvider:
    provider = DaytonaProvider()
    provider._client = client
    return provider


async def test_existing_sandbox_is_adopted_rather_than_recreated():
    running = SimpleNamespace(id="daytona-1", state=SandboxState.STARTED)
    client = _client([running])

    session = await _provider(client).get_or_create_session("thread-7")

    assert session.session_id == "daytona-1"
    client.list.assert_called_once_with(
        labels={
            THREAD_LABEL_KEY: "thread-7",
            PROFILE_LABEL_KEY: SandboxResourceProfile.DEFAULT.value,
        }
    )
    client.create.assert_not_called()


async def test_absent_sandbox_is_created_with_the_thread_label():
    client = _client([])

    await _provider(client).get_or_create_session("thread-7")

    assert client.create.call_args.args[0].labels == {
        THREAD_LABEL_KEY: "thread-7",
        PROFILE_LABEL_KEY: SandboxResourceProfile.DEFAULT.value,
    }


async def test_video_profile_selects_video_snapshot_and_labels(monkeypatch):
    client = _client([])
    monkeypatch.setattr(app_config, "DAYTONA_VIDEO_SNAPSHOT_ID", "video-snapshot-v7")

    await _provider(client).get_or_create_session(
        "thread-7", profile=SandboxResourceProfile.VIDEO_RENDER
    )

    params = client.create.call_args.args[0]
    assert params.snapshot == "video-snapshot-v7"
    assert params.labels == {
        THREAD_LABEL_KEY: "thread-7",
        PROFILE_LABEL_KEY: SandboxResourceProfile.VIDEO_RENDER.value,
    }


async def test_video_profile_requires_a_video_snapshot(monkeypatch):
    client = _client([])
    monkeypatch.setattr(app_config, "DAYTONA_VIDEO_SNAPSHOT_ID", None)

    with pytest.raises(ValueError, match="DAYTONA_VIDEO_SNAPSHOT_ID"):
        await _provider(client).get_or_create_session(
            "thread-7", profile=SandboxResourceProfile.VIDEO_RENDER
        )


@pytest.mark.parametrize("items", [[], [SimpleNamespace(id="daytona-1")]])
async def test_terminate_deletes_only_what_exists(items):
    client = _client(items)

    await _provider(client).terminate_session("thread-7")

    assert client.delete.call_count == len(items)


def test_snapshot_image_must_be_pinned():
    from scripts.create_sandbox_snapshot import resolve_image

    pinned = "ghcr.io/modsetter/surfsense-sandbox:1.2.3"
    assert resolve_image(["prog", pinned], {}) == pinned
    assert resolve_image(["prog"], {"SANDBOX_IMAGE": pinned}) == pinned
    assert (
        resolve_image(["prog", "ghcr.io/x/y@sha256:abc"], {})
        == "ghcr.io/x/y@sha256:abc"
    )

    for rejected in (
        "",
        "ghcr.io/modsetter/surfsense-sandbox:latest",
        # A registry port is not a tag.
        "registry.local:5000/surfsense-sandbox",
    ):
        with pytest.raises(SystemExit):
            resolve_image(["prog", rejected], {})


def test_snapshot_script_builds_versioned_dual_resource_profiles():
    from scripts.create_sandbox_snapshot import snapshot_params

    image = "ghcr.io/modsetter/surfsense-sandbox:1.2.3"
    default, video = snapshot_params(image, {})

    assert default.name == "surfsense-sandbox-1-2-3"
    assert video.name == "surfsense-sandbox-video-1-2-3"
    assert default.image == video.image == image
    assert default.entrypoint == video.entrypoint == ["sleep", "infinity"]
    assert (default.resources.cpu, default.resources.memory, default.resources.disk) == (
        1,
        2,
        10,
    )
    assert (video.resources.cpu, video.resources.memory, video.resources.disk) == (
        4,
        8,
        10,
    )


def test_snapshot_script_does_not_replace_an_existing_snapshot():
    from scripts.create_sandbox_snapshot import _create_if_absent, snapshot_params

    params, _ = snapshot_params(
        "ghcr.io/modsetter/surfsense-sandbox:1.2.3", {}
    )
    snapshots = SimpleNamespace(get=Mock(return_value=object()), create=Mock())
    daytona = SimpleNamespace(snapshot=snapshots)

    _create_if_absent(daytona, params)

    snapshots.create.assert_not_called()
