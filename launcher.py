#!/usr/bin/env python3
"""Cross-platform launcher for the Bilibili Hot 100 dashboard.

Single implementation of the start/stop logic for Windows, macOS and Linux.
The platform scripts (`start-all.bat`, `start-all.sh`, ...) only forward here.

Design notes:
  * Services are spawned with a new process group / detached console, so the
    calling shell (including one that captures stdout through a pipe) can exit
    or continue immediately. This is what makes ``--detached`` reliable for CI
    and AI assistants.
  * Child stdio always goes to ``.pids/*.log``; the parent never inherits its
    own pipe handles into the services.
  * A recorded PID is only stopped after ownership is proven, either by the
    process image living inside this project or by the service answering with
    this project's HTTP signature.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 11)
MIN_NODE = (22, 12)

PROJECT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_DIR / "bilibili-hot100-backend"
FRONTEND_DIR = PROJECT_DIR / "bilibili-hot100-vue3-ts"
PID_DIR = PROJECT_DIR / ".pids"
DEFAULT_DATA_DIR = PROJECT_DIR / "data"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
MAX_LOG_BYTES = 2 * 1024 * 1024

IS_WINDOWS = os.name == "nt"
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

# Owner detection: the service on the port must answer one of these.
SERVICES: dict[str, dict[str, Any]] = {
    "backend": {
        "port": BACKEND_PORT,
        "probe": "/api/status",
        "signatures": ('"total_videos"', '"code"'),
        "needle": "uvicorn",
        "timeout": 60.0,
    },
    "frontend": {
        "port": FRONTEND_PORT,
        "probe": "/",
        "signatures": ("B站热门视频", "bilibili"),
        "needle": "vite",
        "timeout": 60.0,
    },
}

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class LauncherError(RuntimeError):
    """A start/stop step failed in a way the user has to act on."""


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def info(message: str) -> None:
    print(f"  {message}", flush=True)


def step(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f"  [warn] {message}", file=sys.stderr, flush=True)


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_marker(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return ""


def venv_python() -> Path:
    candidates = (
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
        BACKEND_DIR / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if IS_WINDOWS else candidates[1]


def http_probe(port: int, path: str, timeout: float = 1.5) -> tuple[int | None, str]:
    """GET a local URL without going through any configured proxy."""
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with _OPENER.open(url, timeout=timeout) as response:
            return response.status, response.read(65536).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:  # a responding server is still a server
        try:
            body = exc.read(65536).decode("utf-8", "replace")
        except Exception:
            body = ""
        return exc.code, body
    except Exception:
        return None, ""


def port_in_use(port: int) -> bool:
    """True when something actually listens on 127.0.0.1:port.

    A bind test is silent (unlike a probe request), and a failed bind is
    confirmed with a TCP connect so a stale TIME_WAIT socket is not mistaken
    for a running service.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
        return False
    except OSError:
        pass
    finally:
        probe.close()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def listener_pid(port: int) -> int | None:
    """Best-effort lookup of the PID listening on a TCP port."""
    try:
        if IS_WINDOWS:
            output = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            ).stdout
            for line in output.splitlines():
                fields = line.split()
                if len(fields) >= 5 and fields[1].endswith(f":{port}") and fields[3] == "LISTENING":
                    try:
                        return int(fields[4])
                    except ValueError:
                        continue
            return None
        lsof = subprocess.run(
            ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        for line in lsof.stdout.splitlines():
            if line.strip().isdigit():
                return int(line.strip())
    except Exception:
        return None
    return None


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if IS_WINDOWS:
            return _windows_process_handle(pid) is not None
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _windows_process_handle(pid: int) -> Any:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    return kernel32, handle


def process_image(pid: int) -> str:
    """Full image path of a live process, or '' when it cannot be read."""
    if pid <= 0:
        return ""
    try:
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes

            opened = _windows_process_handle(pid)
            if opened is None:
                return ""
            kernel32, handle = opened
            try:
                size = wintypes.DWORD(32768)
                buffer = ctypes.create_unicode_buffer(size.value)
                kernel32.QueryFullProcessImageNameW.argtypes = [
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    wintypes.LPWSTR,
                    ctypes.POINTER(wintypes.DWORD),
                ]
                if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    return buffer.value
                return ""
            finally:
                kernel32.CloseHandle(handle)
        proc_cmdline = Path(f"/proc/{pid}/cmdline")
        if proc_cmdline.exists():
            return proc_cmdline.read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def signature_hit(service: str) -> bool:
    spec = SERVICES[service]
    status, body = http_probe(spec["port"], spec["probe"], timeout=1.0)
    if status != 200 or not body:
        return False
    return any(token in body for token in spec["signatures"])


def pid_file(service: str) -> Path:
    return PID_DIR / f"{service}.pid"


def read_pid(service: str) -> int | None:
    path = pid_file(service)
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw.isdigit():
        path.unlink(missing_ok=True)
        return None
    return int(raw)


def write_pid(service: str, pid: int) -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_file(service).write_text(str(pid), encoding="utf-8")


def clear_pid(service: str) -> None:
    pid_file(service).unlink(missing_ok=True)


def service_state(service: str, trust_signature: bool = True) -> dict[str, Any]:
    """Runs/readiness summary for one service."""
    spec = SERVICES[service]
    port = spec["port"]
    pid = read_pid(service)
    alive = bool(pid and process_alive(pid))
    reachable = port_in_use(port)
    ready = False
    if reachable:
        ready = signature_hit(service) if trust_signature else True
    owned = alive and (is_own_process(pid) or ready)
    return {
        "pid": pid if alive else None,
        "alive": alive,
        "owned": owned,
        "port": port,
        "port_in_use": reachable,
        "ready": ready,
        "url": f"http://127.0.0.1:{port}",
    }


def is_own_process(pid: int | None) -> bool:
    if not pid:
        return False
    image = process_image(pid)
    if not image:
        return False
    normalized = image.replace("\\", "/").lower()
    return str(PROJECT_DIR).replace("\\", "/").lower() in normalized


# --------------------------------------------------------------------------- #
# Dependency bootstrap
# --------------------------------------------------------------------------- #
def ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        required = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}+"
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise LauncherError(
            f"Python {required} is required, current interpreter is {current}. "
            "Install a newer Python and re-run."
        )


def ensure_node() -> None:
    executable = "node.exe" if IS_WINDOWS else "node"
    required = f"{MIN_NODE[0]}.{MIN_NODE[1]}+"
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except OSError as exc:
        raise LauncherError(
            f"Node.js {required} is required but `node` was not found ({exc})."
        ) from exc
    if result.returncode != 0:
        raise LauncherError(f"`node --version` failed; install Node.js {required}.")
    match = re.search(r"v(\d+)\.(\d+)", result.stdout)
    if not match:
        return
    version = (int(match.group(1)), int(match.group(2)))
    if version < MIN_NODE:
        raise LauncherError(f"Node.js {required} is required, found {result.stdout.strip()}.")


def ensure_backend_deps() -> None:
    python = venv_python()
    if not python.exists():
        info("Creating Python virtual environment (.venv)...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(BACKEND_DIR / ".venv")],
            check=False,
        )
        if result.returncode != 0 or not python.exists():
            raise LauncherError("Failed to create the virtual environment.")
        python = venv_python()

    requirements = BACKEND_DIR / "requirements.txt"
    marker = BACKEND_DIR / ".venv" / ".requirements.sha256"
    current = sha256_file(requirements)
    marker_value = read_marker(marker)

    needs_install = current != marker_value
    if not needs_install:
        probe = subprocess.run(
            [str(python), "-c", "import aiofiles, aiohttp, fastapi, pydantic, uvicorn"],
            check=False,
        )
        needs_install = probe.returncode != 0
    if needs_install:
        info("Installing backend dependencies...")
        result = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "-r",
                str(requirements),
            ],
            check=False,
        )
        if result.returncode != 0:
            probe = subprocess.run(
                [str(python), "-c", "import aiofiles, aiohttp, fastapi, pydantic, uvicorn"],
                check=False,
            )
            if probe.returncode != 0:
                raise LauncherError("Backend dependency installation failed.")
            warn("pip reported an error but the backend dependencies already import fine.")
        else:
            marker.write_text(current, encoding="utf-8")


def ensure_frontend_deps() -> None:
    lock_file = FRONTEND_DIR / "package-lock.json"
    node_modules = FRONTEND_DIR / "node_modules"
    vite = node_modules / "vite" / "bin" / "vite.js"
    marker = node_modules / ".package-lock.sha256"
    current = sha256_file(lock_file)
    if node_modules.is_dir() and vite.exists() and read_marker(marker) == current:
        return

    info("Installing frontend dependencies (npm ci)...")
    npm = "npm.cmd" if IS_WINDOWS else "npm"
    result = subprocess.run(
        [npm, "ci", "--no-fund", "--no-audit"], cwd=str(FRONTEND_DIR), check=False
    )
    if result.returncode != 0:
        if vite.exists():
            # node_modules is usable even if npm could not replace a locked file
            # (a running Vite or the antivirus can hold native bindings open).
            warn("npm ci reported an error but node_modules already contains Vite; continuing.")
            return
        raise LauncherError("Frontend dependency installation failed.")
    marker.write_text(current, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Process control
# --------------------------------------------------------------------------- #
def spawn(command: list[str], cwd: Path, service: str, env: dict[str, str]) -> int:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = PID_DIR / f"{service}.out.log"
    stderr_path = PID_DIR / f"{service}.err.log"
    for log in (stdout_path, stderr_path):
        try:
            if log.exists() and log.stat().st_size > MAX_LOG_BYTES:
                log.write_bytes(b"")
        except OSError:
            pass
    kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if IS_WINDOWS:
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    with stdout_path.open("ab") as out, stderr_path.open("ab") as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, **kwargs)  # noqa: S603
    write_pid(service, process.pid)
    return process.pid


def terminate(service: str) -> bool:
    """Stop a service only when ownership can be proven. True when stopped."""
    SERVICES[service]
    pid = read_pid(service)
    if pid is None:
        info(f"{service} is not running.")
        return False
    if not process_alive(pid):
        clear_pid(service)
        info(f"{service} is not running (stale PID file removed).")
        return False
    owned = is_own_process(pid) or signature_hit(service)
    if not owned:
        clear_pid(service)
        raise LauncherError(
            f"Refusing to stop {service} (PID {pid}): it does not look like this project's service."
        )

    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        try:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and process_alive(pid):
            time.sleep(0.2)
        if process_alive(pid):
            try:
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    clear_pid(service)
    info(f"Stopped {service} (PID {pid}).")
    return True


def wait_ready(service: str, timeout: float | None = None) -> None:
    spec = SERVICES[service]
    limit = timeout if timeout is not None else float(spec["timeout"])
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if signature_hit(service):
            return
        time.sleep(0.4)
    pid = read_pid(service)
    raise LauncherError(
        f"{service} did not become ready within {int(limit)} seconds "
        f"(PID {pid}). Check {PID_DIR / (service + '.err.log')}."
    )


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _prune_pid_dir() -> None:
    """Drop the bookkeeping files left after a stop; keep the logs for support."""
    if not PID_DIR.exists():
        return
    (PID_DIR / "services.txt").unlink(missing_ok=True)
    for stale in PID_DIR.glob("*.pid"):
        stale.unlink(missing_ok=True)


def cmd_status(_: argparse.Namespace) -> int:
    payload = {"ok": True, "project": str(PROJECT_DIR)}
    for name in ("backend", "frontend"):
        payload[name] = service_state(name)
    emit(payload)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    step("Stopping Bilibili Hot100 services...")
    failures: list[str] = []
    targets = ["backend", "frontend"] if args.mode == "all" else [args.mode]
    for name in targets:
        try:
            terminate(name)
        except LauncherError as exc:
            failures.append(str(exc))
            warn(str(exc))
    _prune_pid_dir()
    payload = {"ok": not failures, "stopped": targets, "errors": failures}
    if args.json:
        emit(payload)
    return 1 if failures else 0


def cmd_start(args: argparse.Namespace) -> int:
    ensure_python_version()
    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)

    targets = ["backend", "frontend"] if args.mode == "all" else [args.mode]
    started: dict[str, Any] = {}

    if "backend" in targets:
        step(f"Starting backend (FastAPI on :{BACKEND_PORT})...")
        state = service_state("backend")
        if state["owned"]:
            info(f"Backend already running (PID {state['pid']}).")
        else:
            if state["port_in_use"]:
                owner = listener_pid(BACKEND_PORT)
                suffix = f" (PID {owner})" if owner else ""
                raise LauncherError(
                    f"Port {BACKEND_PORT} is already used by another process{suffix}."
                )
            ensure_backend_deps()
            env = os.environ.copy()
            env["BILIBILI_DATA_DIR"] = str(data_dir)
            env.setdefault("PYTHONUNBUFFERED", "1")
            pid = spawn(
                [
                    str(venv_python()),
                    "-m",
                    "uvicorn",
                    "main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(BACKEND_PORT),
                ],
                BACKEND_DIR,
                "backend",
                env,
            )
            info(f"Backend started (PID {pid}).")
        wait_ready("backend")
        info(f"Backend is ready: http://127.0.0.1:{BACKEND_PORT}")
        started["backend"] = {
            "pid": read_pid("backend"),
            "url": f"http://127.0.0.1:{BACKEND_PORT}",
            "ready": True,
        }

    if "frontend" in targets:
        step(f"Starting frontend (Vite on :{FRONTEND_PORT})...")
        state = service_state("frontend")
        if state["owned"]:
            info(f"Frontend already running (PID {state['pid']}).")
        else:
            if state["port_in_use"]:
                owner = listener_pid(FRONTEND_PORT)
                suffix = f" (PID {owner})" if owner else ""
                raise LauncherError(
                    f"Port {FRONTEND_PORT} is already used by another process{suffix}."
                )
            ensure_frontend_deps()
            node = "node.exe" if IS_WINDOWS else "node"
            vite = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
            if not vite.exists():
                raise LauncherError(f"Vite is missing; run `npm ci` in {FRONTEND_DIR}.")
            env = os.environ.copy()
            env["BILIBILI_DATA_DIR"] = str(data_dir)
            pid = spawn(
                [node, str(vite), "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
                FRONTEND_DIR,
                "frontend",
                env,
            )
            info(f"Frontend started (PID {pid}).")
        wait_ready("frontend")
        info(f"Frontend is ready: http://127.0.0.1:{FRONTEND_PORT}")
        started["frontend"] = {
            "pid": read_pid("frontend"),
            "url": f"http://127.0.0.1:{FRONTEND_PORT}",
            "ready": True,
        }

    services_txt = (
        f"Frontend=http://127.0.0.1:{FRONTEND_PORT}\n"
        f"Backend=http://127.0.0.1:{BACKEND_PORT}\n"
        f"Docs=http://127.0.0.1:{BACKEND_PORT}/docs\n"
    )
    (PID_DIR / "services.txt").write_text(services_txt, encoding="utf-8")

    step("Bilibili Hot100 services started successfully.")
    payload = {
        "ok": True,
        "mode": args.mode,
        "detached": bool(args.detached),
        "data_dir": str(data_dir),
        "frontend": started.get("frontend"),
        "backend": started.get("backend"),
    }
    if args.json:
        emit(payload)

    if args.detached:
        return 0

    print(
        f"  Frontend: http://127.0.0.1:{FRONTEND_PORT}\n"
        f"  Backend:  http://127.0.0.1:{BACKEND_PORT}\n"
        f"  Docs:     http://127.0.0.1:{BACKEND_PORT}/docs",
        flush=True,
    )
    print("  Press Ctrl+C to stop the services.", flush=True)
    with contextlib.suppress(Exception):
        webbrowser.open(f"http://127.0.0.1:{FRONTEND_PORT}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("", flush=True)
        for name in ("backend", "frontend"):
            try:
                terminate(name)
            except LauncherError as exc:
                warn(str(exc))
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start, stop or inspect the Bilibili Hot100 services.",
    )
    parser.add_argument("--frontend-only", action="store_true", help="only the Vite dev server")
    parser.add_argument("--backend-only", action="store_true", help="only the FastAPI service")
    parser.add_argument(
        "--detached", action="store_true", help="return immediately, keep services running"
    )
    parser.add_argument(
        "--data-dir", default=str(DEFAULT_DATA_DIR), help="directory for cache and exports"
    )
    parser.add_argument("--json", action="store_true", help="print a machine-readable summary")
    parser.add_argument("--status", action="store_true", help="report service state and exit")
    parser.add_argument("--stop", action="store_true", help="stop the recorded services")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.frontend_only and args.backend_only:
        parser.error("--frontend-only and --backend-only are mutually exclusive")
    args.mode = "frontend" if args.frontend_only else "backend" if args.backend_only else "all"

    try:
        if args.status:
            return cmd_status(args)
        if args.stop:
            return cmd_stop(args)
        return cmd_start(args)
    except LauncherError as exc:
        warn(str(exc))
        if args.json:
            emit({"ok": False, "error": str(exc)})
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
