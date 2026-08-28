"""Fork-safe supervisor for the isolated, warm Kokoro process."""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path

from ..errors import TextToSpeechError
from ..request import SynthesisRequest

_WORKER_MODULE = "app.podcasts.tts.adapters.kokoro_worker"
_MAX_RESPONSE_BYTES = 64 * 1024
_PROCESS_EXIT_SECONDS = 5


class KokoroProcess:
    """Serialize requests through one warm child process per parent process."""

    def __init__(self, *, command: tuple[str, ...] | None = None) -> None:
        self._command = command or (sys.executable, "-m", _WORKER_MODULE)
        self._owner_pid = os.getpid()
        self._executor = self._new_executor()
        self._state_lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._control: socket.socket | None = None
        self._active_token: object | None = None
        atexit.register(self.close)

    async def synthesize(self, request: SynthesisRequest) -> bytes:
        self._reset_after_fork()
        token = object()
        cancelled = threading.Event()
        future = asyncio.get_running_loop().run_in_executor(
            self._executor,
            self._synthesize_sync,
            token,
            cancelled,
            request,
        )
        try:
            return await future
        except asyncio.CancelledError:
            cancelled.set()
            self._stop_if_active(token)
            raise

    def close(self) -> None:
        if os.getpid() != self._owner_pid:
            self._discard_inherited_state()
            return
        self._stop_process()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _synthesize_sync(
        self,
        token: object,
        cancelled: threading.Event,
        request: SynthesisRequest,
    ) -> bytes:
        if cancelled.is_set():
            raise TextToSpeechError("Kokoro synthesis was cancelled")

        workdir = Path(tempfile.mkdtemp(prefix="surfsense-kokoro-"))
        output_path = workdir / "output.wav"
        process: subprocess.Popen[bytes] | None = None
        try:
            with self._state_lock:
                if cancelled.is_set():
                    raise TextToSpeechError("Kokoro synthesis was cancelled")
                process, control = self._ensure_process_locked()
                self._active_token = token

            self._send_request(
                control,
                {
                    "text": request.text,
                    "voice": request.voice,
                    "language": request.language,
                    "speed": request.speed,
                    "output_path": str(output_path),
                },
            )
            response = self._receive_response(control)
            if response == {"ok": True}:
                pass
            elif set(response) == {"ok", "error"} and response["ok"] is False:
                error = response.get("error")
                raise TextToSpeechError(
                    str(error) if error else "Kokoro synthesis failed"
                )
            else:
                raise TextToSpeechError("Kokoro process returned an invalid response")
            audio = output_path.read_bytes()
            if not audio.startswith(b"RIFF"):
                raise TextToSpeechError("Kokoro produced invalid WAV audio")
            return audio
        except TextToSpeechError:
            self._stop_process(expected=process)
            raise
        except Exception as exc:
            self._stop_process(expected=process)
            raise TextToSpeechError(f"Kokoro synthesis failed: {exc}") from exc
        finally:
            with self._state_lock:
                if self._active_token is token:
                    self._active_token = None
            shutil.rmtree(workdir, ignore_errors=True)

    def _reset_after_fork(self) -> None:
        current_pid = os.getpid()
        if current_pid == self._owner_pid:
            return
        self._discard_inherited_state()
        self._owner_pid = current_pid
        self._executor = self._new_executor()
        self._state_lock = threading.Lock()

    def _discard_inherited_state(self) -> None:
        control = self._control
        self._process = None
        self._control = None
        self._active_token = None
        if control is not None:
            control.close()

    @staticmethod
    def _new_executor() -> ThreadPoolExecutor:
        # ponytail: one IPC waiter preserves the existing serialized Kokoro
        # contract; inference itself runs only in the killable child process.
        return ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="surfsense-kokoro-ipc",
        )

    def _ensure_process_locked(
        self,
    ) -> tuple[subprocess.Popen[bytes], socket.socket]:
        if (
            self._process is not None
            and self._control is not None
            and self._process.poll() is None
        ):
            return self._process, self._control

        self._clear_process_locked()
        parent_control, child_control = socket.socketpair()
        try:
            process = subprocess.Popen(
                (*self._command, "--control-fd", str(child_control.fileno())),
                stdin=subprocess.DEVNULL,
                pass_fds=(child_control.fileno(),),
                close_fds=True,
            )
        except Exception:
            parent_control.close()
            raise
        finally:
            child_control.close()

        self._process = process
        self._control = parent_control
        return process, parent_control

    @staticmethod
    def _send_request(control: socket.socket, request: dict[str, object]) -> None:
        control.sendall(
            json.dumps(request, separators=(",", ":"), ensure_ascii=True).encode()
            + b"\n"
        )

    @staticmethod
    def _receive_response(control: socket.socket) -> dict[str, object]:
        response = bytearray()
        while len(response) <= _MAX_RESPONSE_BYTES:
            chunk = control.recv(min(65_536, _MAX_RESPONSE_BYTES + 1 - len(response)))
            if not chunk:
                raise RuntimeError("Kokoro process exited without a response")
            response.extend(chunk)
            if response.endswith(b"\n"):
                decoded = json.loads(response)
                if not isinstance(decoded, dict):
                    raise RuntimeError("Kokoro process returned an invalid response")
                return decoded
        raise RuntimeError("Kokoro process response exceeded the safety limit")

    def _stop_if_active(self, token: object) -> None:
        with self._state_lock:
            if self._active_token is not token:
                return
            process = self._process
        self._stop_process(expected=process)

    def _stop_process(self, *, expected: subprocess.Popen[bytes] | None = None) -> None:
        with self._state_lock:
            process = self._process
            if expected is not None and process is not expected:
                return
            control = self._control
            self._process = None
            self._control = None

        if control is not None:
            control.close()
        if process is None or process.poll() is not None:
            return
        process.kill()
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_PROCESS_EXIT_SECONDS)

    def _clear_process_locked(self) -> None:
        control = self._control
        self._process = None
        self._control = None
        if control is not None:
            control.close()
