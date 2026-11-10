#!/usr/bin/env python3
"""一条命令把项目跑起来：虚拟环境、依赖、前端构建、服务、浏览器。

用法::

    python run.py                 # 默认 8000 端口，自动开浏览器
    python run.py --port 8010     # 换端口
    python run.py --no-browser    # 不自动开浏览器
    python run.py --rebuild       # 强制重新构建前端
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WEB = ROOT / "web"
DIST = WEB / "dist"
REQUIREMENTS = ROOT / "requirements.txt"
MIN_PYTHON = (3, 11)
MIN_NODE = (22, 12)


def step(message: str) -> None:
    print(f"\n{message}", flush=True)


def info(message: str) -> None:
    print(f"  {message}", flush=True)


def fail(message: str) -> int:
    print(f"\n[错误] {message}", file=sys.stderr, flush=True)
    return 1


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def ensure_venv() -> int:
    if not venv_python().exists():
        if sys.version_info < MIN_PYTHON:
            return fail(
                f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+，"
                f"当前是 {sys.version_info.major}.{sys.version_info.minor}"
            )
        step("创建虚拟环境 .venv ...")
        try:
            run([sys.executable, "-m", "venv", str(VENV)])
        except subprocess.CalledProcessError:
            return fail("创建虚拟环境失败，Ubuntu 上可能需要先安装 python3-venv")
        info("完成")

    # 用虚拟环境里的解释器重新执行自己，后续操作都在 .venv 里。
    # Windows 的 os.execv 是“启动新进程再退出当前进程”，会让命令行提前返回，
    # 所以这里统一用子进程等待，Ctrl+C 仍然作用于整个控制台。
    if Path(sys.executable).resolve() != venv_python().resolve():
        result = subprocess.run(
            [str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]], check=False
        )
        return result.returncode

    digest = hashlib.sha256(
        REQUIREMENTS.read_bytes() + f"{sys.version_info[:2]}".encode()
    ).hexdigest()
    marker = VENV / ".requirements"
    installed = marker.exists() and marker.read_text(encoding="utf-8").strip() == digest
    if not installed:
        installed = (
            subprocess.run(
                [sys.executable, "-c", "import aiohttp, fastapi, pydantic, uvicorn"],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
    if installed:
        if not marker.exists():
            marker.write_text(digest, encoding="utf-8")
        return 0

    step("安装后端依赖 ...")
    uv = shutil.which("uv")
    try:
        if uv:
            run([uv, "pip", "install", "--python", sys.executable, "-r", str(REQUIREMENTS)])
        else:
            run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--quiet",
                    "-r",
                    str(REQUIREMENTS),
                ]
            )
    except subprocess.CalledProcessError:
        return fail("后端依赖安装失败")
    marker.write_text(digest, encoding="utf-8")
    info("完成")
    return 0


def newest_mtime(paths: list[Path]) -> float:
    newest = 0.0
    for path in paths:
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
        elif path.is_dir():
            newest = max(newest, newest_mtime(list(path.rglob("*"))))
    return newest


def needs_build() -> bool:
    entry = DIST / "index.html"
    if not entry.exists():
        return True
    sources = [
        WEB / "src",
        WEB / "public",
        WEB / "index.html",
        WEB / "vite.config.ts",
        WEB / "package.json",
        WEB / "package-lock.json",
    ]
    return newest_mtime(sources) > entry.stat().st_mtime


def ensure_web(force: bool) -> int:
    if not needs_build() and not force:
        return 0

    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        return fail("需要 Node.js 22.12+ 才能构建前端：https://nodejs.org")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    try:
        major, minor = (int(part) for part in version.stdout.strip().lstrip("v").split(".")[:2])
    except ValueError:
        return fail(f"无法识别 Node 版本: {version.stdout.strip()}")
    if (major, minor) < MIN_NODE:
        return fail(f"需要 Node.js {MIN_NODE[0]}.{MIN_NODE[1]}+，当前是 {version.stdout.strip()}")

    lock = WEB / "package-lock.json"
    node_modules = WEB / "node_modules"
    marker = node_modules / ".lockhash"
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    if not node_modules.exists() or not marker.exists() or marker.read_text().strip() != digest:
        step("安装前端依赖 ...")
        try:
            run([npm, "ci", "--no-fund", "--no-audit"], cwd=WEB)
        except subprocess.CalledProcessError:
            return fail("前端依赖安装失败")
        marker.write_text(digest, encoding="utf-8")
        info("完成")

    step("构建前端 ...")
    try:
        run([node, "node_modules/vite/bin/vite.js", "build"], cwd=WEB)
    except subprocess.CalledProcessError:
        return fail("前端构建失败")
    info("完成")
    return 0


def port_owner(port: int) -> int | None:
    try:
        if os.name == "nt":
            output = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, check=False
            ).stdout
            for line in output.splitlines():
                fields = line.split()
                if len(fields) >= 5 and fields[1].endswith(f":{port}") and fields[3] == "LISTENING":
                    return int(fields[4])
        else:
            output = subprocess.run(
                ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            for line in output.splitlines():
                if line.strip().isdigit():
                    return int(line.strip())
    except (OSError, ValueError):
        return None
    return None


def port_free(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 B站热门视频看板")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--rebuild", action="store_true", help="强制重新构建前端")
    parser.add_argument("--data-dir", help="数据目录（默认 data/）")
    args = parser.parse_args()

    code = ensure_venv()
    if code:
        return code
    code = ensure_web(args.rebuild)
    if code:
        return code

    if args.data_dir:
        os.environ["BILIBILI_DATA_DIR"] = str(Path(args.data_dir).expanduser().resolve())
    if not port_free(args.port):
        owner = port_owner(args.port)
        suffix = f"（PID {owner}）" if owner else ""
        return fail(f"端口 {args.port} 已被占用{suffix}，换一个端口：--port 8010")

    url = f"http://127.0.0.1:{args.port}"
    print(f"\n  B站热门视频: {url}")
    print(f"  数据目录:   {os.getenv('BILIBILI_DATA_DIR', str(ROOT / 'data'))}")
    print("  按 Ctrl+C 停止\n", flush=True)

    if not args.no_browser:
        threading.Timer(1.2, webbrowser.open, args=[url]).start()

    import uvicorn

    uvicorn.run("server.app:app", host="127.0.0.1", port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已停止", flush=True)
        raise SystemExit(0) from None
