"""内存缓存、快照持久化和刷新编排。"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from datetime import datetime
from typing import Any

from . import config, crawler, images
from .logs import log_error, log_info, log_success, log_warning

cache: dict[str, Any] = {
    "videos": [],
    "update_time": None,
    "is_partial": False,
    "source": None,
    "is_updating": False,
    "last_error": None,
}

_task: asyncio.Task[None] | None = None
_lock = asyncio.Lock()


def iso_timestamp(timestamp: float) -> str:
    """带时区的本地时间，浏览器能直接解析。"""
    try:
        return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return datetime.now().astimezone().isoformat(timespec="seconds")


def is_stale() -> bool:
    update_time = cache["update_time"]
    if not update_time:
        return True
    return time.time() - update_time > config.CACHE_TTL_SECONDS


def publish(videos: list[dict], update_time: float, is_partial: bool, source: str) -> None:
    cache.update(
        videos=videos,
        update_time=update_time,
        is_partial=is_partial,
        source=source,
        last_error=None,
    )


def reset() -> None:
    """测试用：清空内存状态，不碰磁盘。"""
    cache.update(
        videos=[],
        update_time=None,
        is_partial=False,
        source=None,
        is_updating=False,
        last_error=None,
    )


def _atomic_write(path, data: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(data, encoding="utf-8")
    temporary.replace(path)


async def save_snapshot(videos: list[dict], update_time: float, is_partial: bool) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": iso_timestamp(time.time()),
        "update_time": update_time,
        "is_partial": is_partial,
        "total": len(videos),
        "videos": videos,
    }
    try:
        await asyncio.to_thread(
            _atomic_write,
            config.SNAPSHOT_FILE,
            json.dumps(payload, ensure_ascii=False),
        )
    except OSError as exc:
        log_warning(f"快照写入失败: {exc}")


def load_snapshot() -> tuple[list[dict], float, bool] | None:
    path = config.SNAPSHOT_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log_warning(f"快照读取失败，忽略: {exc}")
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("videos"), list):
        return None

    try:
        videos = crawler.normalize_videos(
            [video for video in payload["videos"] if isinstance(video, dict)]
        )
    except Exception as exc:
        log_warning(f"快照不可用，忽略: {exc}")
        return None

    update_time = payload.get("update_time")
    if not isinstance(update_time, (int, float)):
        try:
            update_time = path.stat().st_mtime
        except OSError:
            update_time = time.time()

    log_success(f"已从快照恢复 {len(videos)} 条视频")
    return videos, float(update_time), bool(payload.get("is_partial"))


async def refresh() -> None:
    """抓一次并写快照；失败保留现有数据。"""
    async with _lock:
        cache["is_updating"] = True
        cache["last_error"] = None
        try:
            videos, is_partial, captured_at = await crawler.crawl()
            await save_snapshot(videos, captured_at, is_partial)
            publish(videos, captured_at, is_partial, "live")
            images.prune(images.urls_for(videos))
            log_success(f"刷新完成: {len(videos)} 个视频")
        except Exception as exc:
            cache["last_error"] = str(exc)
            log_error(f"刷新失败，保留现有数据: {exc}")
            raise
        finally:
            cache["is_updating"] = False


def schedule() -> bool:
    """启动一次后台刷新；已有任务在跑则返回 False。"""
    global _task
    if _task and not _task.done():
        return False
    cache["is_updating"] = True
    cache["last_error"] = None
    _task = asyncio.create_task(refresh())
    _task.add_done_callback(_consume)
    return True


def _consume(task: asyncio.Task[None]) -> None:
    if not task.cancelled():
        task.exception()


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        with suppress(asyncio.CancelledError):
            await _task
    _task = None


def status() -> dict[str, Any]:
    return {
        "total": len(cache["videos"]),
        "update_time": iso_timestamp(cache["update_time"]) if cache["update_time"] else None,
        "is_updating": cache["is_updating"],
        "is_partial": cache["is_partial"],
        "source": cache["source"],
        "last_error": cache["last_error"],
        "stale": is_stale(),
        "cached_images": len(images.files),
        "data_dir": str(config.DATA_DIR),
        "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
    }


def startup() -> None:
    """加载磁盘上的快照并发布到内存。"""
    loaded = load_snapshot()
    if loaded:
        videos, update_time, is_partial = loaded
        publish(videos, update_time, is_partial, "snapshot")
    log_info("热门视频服务已启动")
