"""环形日志缓冲 + WebSocket 广播。"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from datetime import datetime

from fastapi import WebSocket

MAX_ENTRIES = 500
QUEUE_SIZE = 1000


class LogManager:
    def __init__(self, max_size: int = MAX_ENTRIES) -> None:
        self.logs: deque[dict] = deque(maxlen=max_size)
        self.clients: set[WebSocket] = set()
        self.queue: asyncio.Queue[dict] | None = None
        self.worker: asyncio.Task[None] | None = None
        self.send_lock = asyncio.Lock()

    async def start(self) -> None:
        self.queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self.worker = asyncio.create_task(self._broadcast())

    async def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            with suppress(asyncio.CancelledError):
                await self.worker
        self.worker = None
        self.queue = None
        self.clients.clear()

    def add(self, level: str, message: str) -> None:
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

    async def _broadcast(self) -> None:
        assert self.queue is not None
        while True:
            entry = await self.queue.get()
            if not self.clients:
                continue
            payload = {"type": "log", "data": entry}
            targets = list(self.clients)
            async with self.send_lock:
                results = await asyncio.gather(
                    *(client.send_json(payload) for client in targets),
                    return_exceptions=True,
                )
            for client, result in zip(targets, results, strict=True):
                if isinstance(result, Exception):
                    self.clients.discard(client)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)
        # 历史日志和后续广播共用一把发送锁，避免同一连接上帧交错。
        async with self.send_lock:
            for entry in list(self.logs):
                await websocket.send_json({"type": "log", "data": entry})

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    def clear(self) -> None:
        self.logs.clear()


log_manager = LogManager()


def log_info(message: str) -> None:
    log_manager.add("INFO", message)


def log_success(message: str) -> None:
    log_manager.add("SUCCESS", message)


def log_warning(message: str) -> None:
    log_manager.add("WARNING", message)


def log_error(message: str) -> None:
    log_manager.add("ERROR", message)
