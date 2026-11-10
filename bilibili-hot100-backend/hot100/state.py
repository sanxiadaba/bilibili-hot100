"""Refresh orchestration and the in-memory cache shared by the API routes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Any
from uuid import uuid4

from .crawler import CrawlError, crawl_hot100
from .logs import log_error, log_success

cache: dict[str, Any] = {
    "data": [],
    "update_time": None,
    "is_updating": False,
    "refresh_id": None,
    "last_error": None,
    "is_partial": False,
    "source": None,
    "snapshot_time": None,
}
refresh_lock = asyncio.Lock()
current_refresh_task: asyncio.Task[None] | None = None


def apply_snapshot(payload: dict[str, Any]) -> None:
    """Seed the cache from a snapshot loaded during startup."""
    cache["data"] = payload["videos"]
    cache["update_time"] = payload["update_time"]
    cache["is_partial"] = payload.get("is_partial", False)
    cache["source"] = payload.get("source", "snapshot")
    cache["snapshot_time"] = payload.get("saved_at")
    cache["last_error"] = None


def reset_cache() -> None:
    cache.update(
        data=[],
        update_time=None,
        is_updating=False,
        refresh_id=None,
        last_error=None,
        is_partial=False,
        source=None,
        snapshot_time=None,
    )


async def _run_refresh(refresh_id: str) -> None:
    async with refresh_lock:
        try:
            videos, is_partial, captured_at = await crawl_hot100()
            cache["data"] = videos
            cache["update_time"] = captured_at
            cache["is_partial"] = is_partial
            cache["source"] = "live"
            cache["snapshot_time"] = iso_timestamp(captured_at)
            cache["last_error"] = None
            log_success(f"刷新完成: {len(videos)} 个视频")
        except Exception as exc:
            cache["last_error"] = str(exc)
            log_error(f"刷新失败，保留现有缓存: {exc}")
            raise
        finally:
            if cache["refresh_id"] == refresh_id:
                cache["is_updating"] = False


def iso_timestamp(timestamp: float) -> str:
    """Local, timezone-aware ISO timestamp (the browser can parse the offset)."""
    try:
        return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return datetime.now().astimezone().isoformat(timespec="seconds")


def schedule_refresh() -> tuple[asyncio.Task[None], bool]:
    global current_refresh_task
    if current_refresh_task and not current_refresh_task.done():
        return current_refresh_task, False
    refresh_id = uuid4().hex
    cache["refresh_id"] = refresh_id
    cache["is_updating"] = True
    cache["last_error"] = None
    current_refresh_task = asyncio.create_task(_run_refresh(refresh_id))
    current_refresh_task.add_done_callback(_consume_refresh_exception)
    return current_refresh_task, True


def _consume_refresh_exception(task: asyncio.Task[None]) -> None:
    """Retrieve background failures after state and logs have captured them."""
    if not task.cancelled():
        task.exception()


async def stop_refresh_task() -> None:
    global current_refresh_task
    if current_refresh_task and not current_refresh_task.done():
        current_refresh_task.cancel()
        with suppress(asyncio.CancelledError):
            await current_refresh_task
    current_refresh_task = None


__all__ = [
    "CrawlError",
    "apply_snapshot",
    "cache",
    "refresh_lock",
    "reset_cache",
    "schedule_refresh",
    "stop_refresh_task",
]
