"""日志管理器：清空语义与连接回滚。"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock

from server.logs import LogManager


class LogManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_drains_pending_broadcast_queue(self):
        manager = LogManager()
        manager.queue = asyncio.Queue()
        manager.add("INFO", "before clear")

        manager.clear()

        self.assertEqual(len(manager.logs), 0)
        self.assertEqual(manager.queue.qsize(), 0)

    async def test_connect_rolls_back_client_when_history_fails(self):
        manager = LogManager()
        manager.logs.append({"time": "00:00:00.000", "level": "INFO", "message": "x"})
        websocket = AsyncMock()
        websocket.send_json.side_effect = RuntimeError("closed")

        with self.assertRaises(RuntimeError):
            await manager.connect(websocket)

        self.assertNotIn(websocket, manager.clients)


if __name__ == "__main__":
    unittest.main()
