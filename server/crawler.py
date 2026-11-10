"""抓取 B站热门榜：并发取两页、去重、校验，再把封面/头像落到本地。"""

from __future__ import annotations

import asyncio
import time

import aiohttp

from . import config, images
from .logs import log_info, log_success, log_warning
from .models import VideoItem


class CrawlError(RuntimeError):
    """拿不到一份可用的榜单。"""


async def _fetch_once(session: aiohttp.ClientSession, page: int, page_size: int) -> list[dict]:
    timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
    async with session.get(
        config.BILIBILI_API,
        params={"ps": page_size, "pn": page},
        headers=config.HEADERS,
        timeout=timeout,
    ) as response:
        if response.status != 200:
            raise CrawlError(f"HTTP {response.status}")
        # content_type=None：风控页会返回 text/html，让解析错误走重试而不是直接抛。
        payload = await response.json(content_type=None)

    if not isinstance(payload, dict):
        raise CrawlError("返回格式异常")
    if payload.get("code") != 0:
        raise CrawlError(f"接口错误: {payload.get('message') or payload.get('code')}")
    data = payload.get("data")
    videos = data.get("list") if isinstance(data, dict) else None
    if not isinstance(videos, list) or not videos:
        raise CrawlError("返回了空列表")
    if len(videos) != page_size:
        log_warning(f"第 {page} 页只返回 {len(videos)} 条")
    return videos


async def fetch_page(
    session: aiohttp.ClientSession, page: int, page_size: int = config.PAGE_SIZE
) -> list[dict]:
    """单页请求，失败按 RETRY_DELAYS 重试。"""
    last_error: Exception | None = None
    for attempt in range(len(config.RETRY_DELAYS) + 1):
        try:
            videos = await _fetch_once(session, page, page_size)
            log_success(f"第 {page} 页获取成功: {len(videos)} 个视频")
            return videos
        except (CrawlError, aiohttp.ClientError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt >= len(config.RETRY_DELAYS):
                break
            delay = config.RETRY_DELAYS[attempt]
            log_warning(f"第 {page} 页请求失败，{delay} 秒后重试: {exc}")
            await asyncio.sleep(delay)
    raise CrawlError(f"第 {page} 页抓取失败: {last_error}")


def normalize_videos(videos: list[dict]) -> list[dict]:
    """去重、丢掉字段坏掉的条目、重新编号；少于 MIN_VIDEOS 视为失败。"""
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
            item = VideoItem.model_validate({**video, "rank": len(normalized) + 1})
        except Exception as exc:
            skipped += 1
            log_warning(f"跳过字段无效的视频 {bvid}: {str(exc).splitlines()[0]}")
            continue
        seen.add(bvid)
        normalized.append(item.model_dump())

    if skipped:
        log_warning(f"跳过 {skipped} 条字段无效的视频")
    if duplicates:
        log_warning(f"去除 {duplicates} 条重复 BV 号")
    if len(normalized) < config.MIN_VIDEOS:
        raise CrawlError(
            f"热门数据不完整: 期望至少 {config.MIN_VIDEOS} 条，实际 {len(normalized)} 条"
        )
    return normalized


async def crawl() -> tuple[list[dict], bool, float]:
    """抓取一份完整榜单，返回 ``(videos, is_partial, captured_at)``。"""
    log_info("开始抓取 B站热门视频")
    started = time.monotonic()
    async with aiohttp.ClientSession() as session:
        pages = await asyncio.gather(
            *(fetch_page(session, page) for page in range(1, config.PAGE_COUNT + 1))
        )
        videos = normalize_videos([video for page in pages for video in page])
        await images.download_all(session, images.urls_for(videos))

    is_partial = len(videos) < config.TARGET_VIDEOS
    if is_partial:
        log_warning(f"本次仅获得 {len(videos)} 条视频，标记为不完整")
    log_success(f"抓取完成: {len(videos)} 个视频, 耗时 {time.monotonic() - started:.2f} 秒")
    return videos, is_partial, time.time()
