"""In-memory log ring buffer plus WebSocket fan-out.

The buffer powers ``/api/logs`` and the WebSocket history replay; every write
also feeds a bounded queue consumed by a single broadcast task.
"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from datetime import datetime

from fastapi import WebSocket

MAX_LOG_ENTRIES = 500
QUEUE_SIZE = 1000


class LogManager:
    def __init__(self, max_size: int = MAX_LOG_ENTRIES):
        self.logs: deque[dict] = deque(maxlen=max_size)
        self.websockets: list[WebSocket] = []
        self.lock = asyncio.Lock()
        self.send_lock = asyncio.Lock()
        self.queue: asyncio.Queue[dict] | None = None
        self.worker: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self.worker = asyncio.create_task(self._broadcast_loop())

    async def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            with suppress(asyncio.CancelledError):
                await self.worker
        self.worker = None
        self.queue = None

    def add_log(self, level: str, message: str) -> None:
        entry = {
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        if not self.queue:
            return
        if self.queue.full():
            with suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
        self.queue.put_nowait(entry)

    async def _broadcast_loop(self) -> None:
        assert self.queue is not None
        while True:
            entry = await self.queue.get()
            async with self.lock:
                connections = list(self.websockets)
            if not connections:
                continue
            payload = {"type": "log", "data": entry}
            async with self.send_lock:
                results = await asyncio.gather(
                    *(self._safe_send(ws, payload) for ws in connections),
                    return_exceptions=True,
                )
            disconnected = [
                ws
                for ws, result in zip(connections, results, strict=True)
                if isinstance(result, Exception)
            ]
            if disconnected:
                async with self.lock:
                    self.websockets = [ws for ws in self.websockets if ws not in disconnected]

    @staticmethod
    async def _safe_send(websocket: WebSocket, payload: dict) -> None:
        await websocket.send_json(payload)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.websockets.append(websocket)
            history = list(self.logs)
        # Holding send_lock keeps history replay from interleaving with a
        # broadcast frame on the same socket.
        async with self.send_lock:
            for entry in history:
                await websocket.send_json({"type": "log", "data": entry})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.lock:
            if websocket in self.websockets:
                self.websockets.remove(websocket)

    def get_logs(self) -> list[dict]:
        return list(self.logs)

    def clear(self) -> None:
        self.logs.clear()


log_manager = LogManager()


def log_info(message: str) -> None:
    log_manager.add_log("INFO", message)


def log_success(message: str) -> None:
    log_manager.add_log("SUCCESS", message)


def log_warning(message: str) -> None:
    log_manager.add_log("WARNING", message)


def log_error(message: str) -> None:
    log_manager.add_log("ERROR", message)


def log_debug(message: str) -> None:
    log_manager.add_log("DEBUG", message)


def log_snapshot() -> list[dict[str, str]]:
    return log_manager.get_logs()
