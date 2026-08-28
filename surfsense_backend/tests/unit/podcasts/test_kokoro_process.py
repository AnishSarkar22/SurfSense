from __future__ import annotations

import asyncio
import socket
import sys
from pathlib import Path

import pytest

from app.podcasts.tts.adapters import kokoro_process
from app.podcasts.tts.adapters.kokoro_process import KokoroProcess
from app.podcasts.tts.errors import TextToSpeechError
from app.podcasts.tts.request import SynthesisRequest

_FAKE_WORKER = r"""
import argparse
import json
import os
import socket
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--marker", required=True)
parser.add_argument("--control-fd", type=int, required=True)
args = parser.parse_args()
with open(args.marker, "a", encoding="utf-8") as marker:
    marker.write(f"{os.getpid()}\n")

control = socket.socket(fileno=args.control_fd)
buffer = bytearray()
while True:
    chunk = control.recv(65536)
    if not chunk:
        break
    buffer.extend(chunk)
    while b"\n" in buffer:
        line, _, rest = buffer.partition(b"\n")
        buffer = bytearray(rest)
        request = json.loads(line)
        output = Path(request["output_path"])
        if request["text"] == "hang":
            time.sleep(60)
        elif request["text"] == "slow":
            time.sleep(0.03)
            output.write_bytes(b"RIFF-test")
            control.sendall(b'{"ok":true}\n')
        elif request["text"] == "crash":
            output.with_suffix(".wav.partial").write_bytes(b"partial")
            os._exit(17)
        elif request["text"] == "error":
            control.sendall(b'{"ok":false,"error":"model failed"}\n')
        else:
            output.write_bytes(b"RIFF-test")
            control.sendall(b'{"ok":true}\n')
"""


def _runner(tmp_path: Path) -> tuple[KokoroProcess, Path]:
    marker = tmp_path / "starts.txt"
    return (
        KokoroProcess(
            command=(
                sys.executable,
                "-c",
                _FAKE_WORKER,
                "--marker",
                str(marker),
            )
        ),
        marker,
    )


def _request(text: str = "hello") -> SynthesisRequest:
    return SynthesisRequest(text, "af_heart", "en-US")


async def _wait_until_started(runner: KokoroProcess) -> None:
    for _ in range(100):
        if runner._active_token is not None and runner._process is not None:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Kokoro child did not start")


async def test_success_reuses_one_warm_process(tmp_path):
    runner, marker = _runner(tmp_path)
    try:
        assert await runner.synthesize(_request("one")) == b"RIFF-test"
        assert await runner.synthesize(_request("two")) == b"RIFF-test"
        assert len(marker.read_text().splitlines()) == 1
    finally:
        runner.close()


async def test_concurrent_requests_are_serialized_through_one_process(tmp_path):
    runner, marker = _runner(tmp_path)
    try:
        results = await asyncio.gather(
            runner.synthesize(_request("slow")),
            runner.synthesize(_request("slow")),
        )
        assert results == [b"RIFF-test", b"RIFF-test"]
        assert len(marker.read_text().splitlines()) == 1
    finally:
        runner.close()


async def test_failure_is_one_attempt_and_next_request_gets_fresh_process(tmp_path):
    runner, marker = _runner(tmp_path)
    try:
        with pytest.raises(TextToSpeechError, match="model failed"):
            await runner.synthesize(_request("error"))
        assert len(marker.read_text().splitlines()) == 1

        assert await runner.synthesize(_request("next")) == b"RIFF-test"
        assert len(marker.read_text().splitlines()) == 2
    finally:
        runner.close()


async def test_crash_fails_once_and_removes_partial_output(tmp_path, monkeypatch):
    workdirs: list[Path] = []

    def make_workdir(*, prefix: str) -> str:
        path = tmp_path / f"{prefix}{len(workdirs)}"
        path.mkdir()
        workdirs.append(path)
        return str(path)

    monkeypatch.setattr(kokoro_process.tempfile, "mkdtemp", make_workdir)
    runner, marker = _runner(tmp_path)
    try:
        with pytest.raises(TextToSpeechError, match="exited without a response"):
            await runner.synthesize(_request("crash"))

        assert len(marker.read_text().splitlines()) == 1
        assert workdirs
        assert all(not path.exists() for path in workdirs)
    finally:
        runner.close()


async def test_cancellation_kills_child_and_cleans_output(tmp_path, monkeypatch):
    workdirs: list[Path] = []

    def make_workdir(*, prefix: str) -> str:
        path = tmp_path / f"{prefix}{len(workdirs)}"
        path.mkdir()
        workdirs.append(path)
        return str(path)

    monkeypatch.setattr(kokoro_process.tempfile, "mkdtemp", make_workdir)
    runner, _marker = _runner(tmp_path)
    task = asyncio.create_task(runner.synthesize(_request("hang")))
    await _wait_until_started(runner)
    process = runner._process

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    for _ in range(100):
        if process is not None and process.poll() is not None:
            break
        await asyncio.sleep(0.01)

    assert process is not None and process.poll() is not None
    for _ in range(100):
        if workdirs and all(not path.exists() for path in workdirs):
            break
        await asyncio.sleep(0.01)
    assert workdirs and all(not path.exists() for path in workdirs)
    runner.close()


def test_fork_guard_discards_inherited_child_without_killing_it(monkeypatch):
    runner = KokoroProcess()
    inherited_parent, inherited_child = socket.socketpair()
    old_executor = runner._executor

    class InheritedProcess:
        def __init__(self) -> None:
            self.killed = False

        def kill(self) -> None:
            self.killed = True

    inherited_process = InheritedProcess()
    runner._process = inherited_process  # type: ignore[assignment]
    runner._control = inherited_parent
    monkeypatch.setattr(kokoro_process.os, "getpid", lambda: runner._owner_pid + 1)

    runner._reset_after_fork()

    assert runner._process is None
    assert runner._control is None
    assert not inherited_process.killed
    assert runner._executor is not old_executor
    inherited_child.close()
    old_executor.shutdown(wait=False, cancel_futures=True)
    runner.close()


def test_worker_exits_when_parent_control_socket_closes(tmp_path):
    runner, _marker = _runner(tmp_path)

    async def start() -> None:
        assert await runner.synthesize(_request()) == b"RIFF-test"

    asyncio.run(start())
    process = runner._process
    control = runner._control
    assert process is not None and control is not None

    control.close()
    for _ in range(100):
        if process.poll() is not None:
            break
        import time

        time.sleep(0.01)

    assert process.poll() is not None
    runner._process = None
    runner._control = None
    runner.close()
