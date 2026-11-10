"""Fetching, validating and enriching the Bilibili popular list."""

from __future__ import annotations

import asyncio
import time

import aiohttp

from . import config, images, storage
from .logs import log_info, log_success, log_warning
from .models import VideoItem


class CrawlError(RuntimeError):
    """Raised when a complete, valid TOP 100 snapshot cannot be produced."""


async def _fetch_page_once(session: aiohttp.ClientSession, page: int, page_size: int) -> list[dict]:
    url = f"{config.BILIBILI_API}/x/web-interface/popular"
    params = {"ps": page_size, "pn": page}
    try:
        timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT_SECONDS)
        async with session.get(
            url, params=params, headers=config.HEADERS, timeout=timeout
        ) as response:
            if response.status != 200:
                raise CrawlError(f"HTTP {response.status}")
            payload = await response.json()
    except TimeoutError as exc:
        raise CrawlError("请求超时") from exc
    except aiohttp.ClientError as exc:
        raise CrawlError(f"网络异常: {exc}") from exc

    if payload.get("code") != 0:
        raise CrawlError(f"API 错误: {payload.get('message', 'unknown')}")
    videos = payload.get("data", {}).get("list")
    if not isinstance(videos, list) or not videos:
        raise CrawlError("返回了空列表")
    if len(videos) != page_size:
        log_warning(f"第 {page} 页返回 {len(videos)} 条，少于期望的 {page_size} 条")
    return videos


async def fetch_page(
    session: aiohttp.ClientSession,
    page: int,
    page_size: int = config.FETCH_PAGE_SIZE,
) -> list[dict]:
    """Fetch one page, retrying transient failures with a short backoff."""
    last_error: CrawlError | None = None
    for attempt in range(len(config.RETRY_DELAYS) + 1):
        try:
            videos = await _fetch_page_once(session, page, page_size)
            log_success(f"第 {page} 页获取成功: {len(videos)} 个视频")
            return videos
        except CrawlError as exc:
            last_error = CrawlError(f"第 {page} 页{exc}")
            if attempt < len(config.RETRY_DELAYS):
                delay = config.RETRY_DELAYS[attempt]
                log_warning(f"第 {page} 页请求失败，{delay} 秒后重试: {exc}")
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


def normalize_videos(videos: list[dict]) -> list[dict]:
    """Drop duplicates and unusable entries, then require a usable snapshot.

    A single bad item must not discard an otherwise good TOP 100, but a list
    that lost a whole page (fewer than ``MIN_VIDEOS`` items) is still a failure.
    """
    seen: set[str] = set()
    normalized: list[dict] = []
    skipped = 0
    duplicates = 0
    for video in videos:
        if not isinstance(video, dict):
            skipped += 1
            continue
        bvid = video.get("bvid")
        if not isinstance(bvid, str) or not bvid:
            skipped += 1
            continue
        if bvid in seen:
            duplicates += 1
            continue
        try:
            VideoItem.model_validate({**video, "rank": len(normalized) + 1})
        except Exception as exc:
            skipped += 1
            log_warning(f"跳过字段无效的视频 {bvid}: {str(exc).splitlines()[0]}")
            continue
        seen.add(bvid)
        video["rank"] = len(normalized) + 1
        normalized.append(video)

    if skipped:
        log_warning(f"跳过 {skipped} 条字段无效的视频")
    if duplicates:
        log_warning(f"去除 {duplicates} 条重复 BV 号")
    if len(normalized) < config.MIN_VIDEOS:
        raise CrawlError(
            f"热门数据不完整: 期望至少 {config.MIN_VIDEOS} 条，实际 {len(normalized)} 条"
        )
    return normalized


async def crawl_hot100() -> tuple[list[dict], bool, float]:
    """Crawl the popular list; returns ``(videos, is_partial, captured_at)``."""
    log_info("开始爬取 B站热门视频 TOP 100")
    started = time.monotonic()
    async with aiohttp.ClientSession() as session:
        pages = await asyncio.gather(
            *(fetch_page(session, page) for page in range(1, config.PAGE_COUNT + 1))
        )
        videos = normalize_videos([video for page in pages for video in page])
        is_partial = len(videos) < config.TARGET_VIDEOS
        captured_at = time.time()

        # The snapshot and the export keep the original image URLs, so both stay
        # portable; the image cache rewrites them only in memory afterwards.
        await storage.save_snapshot(videos, captured_at, is_partial)
        export_path = await storage.export_data_to_json(videos)
        if is_partial:
            log_warning(f"本次仅获得 {len(videos)} 条视频，已标记为不完整数据")
        await images.cache_video_images(session, videos)

    await asyncio.to_thread(storage.prune_exports)
    await asyncio.to_thread(images.prune_orphans)

    log_success(f"数据爬取完成: {len(videos)} 个视频, 耗时 {time.monotonic() - started:.2f} 秒")
    if export_path:
        log_info(f"JSON 数据已导出: {export_path}")
    return videos, is_partial, captured_at
