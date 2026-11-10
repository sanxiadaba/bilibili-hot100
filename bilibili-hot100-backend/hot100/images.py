"""Content-addressed image cache for covers and UP avatars."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiofiles
import aiohttp

from . import config
from .logs import log_info, log_success, log_warning
from .paths import safe_child

image_index: dict[str, str] = {}
image_files_by_name: dict[str, Path] = {}


class ImageCacheError(RuntimeError):
    """Raised when a single image cannot be stored (never fatal for a crawl)."""


def normalize_image_url(url: str) -> str:
    return url.replace("http://", "https://", 1)


def _image_extension(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "gif"} else "jpg"


def _image_filename(url: str) -> str:
    normalized = normalize_image_url(url)
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return f"{digest}.{_image_extension(normalized)}"


def rebuild_image_index() -> None:
    """Build the URL-to-file index and migrate the legacy URL list."""
    image_index.clear()
    image_files_by_name.clear()
    for path in config.IMAGE_CACHE_DIR.glob("*/*"):
        if path.is_file():
            image_files_by_name[path.name] = path

    raw: Any = {}
    if config.IMAGE_INDEX_FILE.exists():
        try:
            raw = json.loads(config.IMAGE_INDEX_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_warning(f"图片缓存索引读取失败，将重建: {exc}")

    if isinstance(raw, dict):
        for url, relative_path in raw.items():
            if not isinstance(url, str) or not isinstance(relative_path, str):
                continue
            path = safe_child(config.IMAGE_CACHE_DIR, relative_path)
            if path and path.is_file():
                image_index[normalize_image_url(url)] = relative_path.replace("\\", "/")
    elif isinstance(raw, list):
        for url in raw:
            if isinstance(url, str):
                resolve_cached_image(url)

    if image_index:
        log_info(f"已加载 {len(image_index)} 个有效图片缓存")


def resolve_cached_image(url: str) -> str | None:
    """Return the local ``/api/images/...`` URL for a cached image, if any."""
    normalized = normalize_image_url(url)
    relative_path = image_index.get(normalized)
    if relative_path:
        path = safe_child(config.IMAGE_CACHE_DIR, relative_path)
        if path and path.is_file():
            return f"/api/images/{relative_path.replace(os.sep, '/')}"
        image_index.pop(normalized, None)

    filenames = {_image_filename(url)}
    original_digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    filenames.add(f"{original_digest}.{_image_extension(url)}")
    for filename in filenames:
        path = image_files_by_name.get(filename)
        if path and path.is_file():
            relative = path.relative_to(config.IMAGE_CACHE_DIR).as_posix()
            image_index[normalized] = relative
            return f"/api/images/{relative}"
    return None


def save_image_index() -> None:
    index_file = config.IMAGE_INDEX_FILE
    index_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_file.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(image_index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, index_file)


async def download_image(session: aiohttp.ClientSession, url: str) -> tuple[str, bool]:
    """Download one image; returns ``(served_url, was_cached)``."""
    cached_url = resolve_cached_image(url)
    if cached_url:
        return cached_url, True

    normalized = normalize_image_url(url)
    date = datetime.now().strftime("%Y%m%d")
    date_dir = config.IMAGE_CACHE_DIR / date
    date_dir.mkdir(parents=True, exist_ok=True)
    filename = _image_filename(normalized)
    target = date_dir / filename
    temporary = target.with_suffix(target.suffix + ".tmp")

    try:
        timeout = aiohttp.ClientTimeout(total=config.IMAGE_TIMEOUT_SECONDS)
        async with session.get(normalized, headers=config.HEADERS, timeout=timeout) as response:
            if response.status != 200:
                raise ImageCacheError(f"HTTP {response.status}")
            content = await response.read()
            if not content:
                raise ImageCacheError("响应内容为空")
        async with aiofiles.open(temporary, "wb") as file:
            await file.write(content)
        await asyncio.to_thread(os.replace, temporary, target)
        relative = target.relative_to(config.IMAGE_CACHE_DIR).as_posix()
        image_index[normalized] = relative
        image_files_by_name[filename] = target
        return f"/api/images/{relative}", False
    except Exception as exc:
        with suppress(OSError):
            temporary.unlink()
        log_warning(f"图片下载失败: {url[:60]} ({exc})")
        return url, False


async def cache_video_images(session: aiohttp.ClientSession, videos: list[dict]) -> None:
    """Download covers/avatars once per URL and rewrite ``pic``/``face`` in place."""
    references: dict[str, dict[str, Any]] = {}
    for video in videos:
        targets = [(video, "pic")]
        owner = video.get("owner")
        if isinstance(owner, dict):
            targets.append((owner, "face"))
        for item, key in targets:
            url = item.get(key)
            if not isinstance(url, str) or not url:
                continue
            normalized = normalize_image_url(url)
            record = references.setdefault(normalized, {"url": url, "targets": []})
            record["targets"].append((item, key))

    semaphore = asyncio.Semaphore(config.IMAGE_CONCURRENCY)

    async def download(record: dict[str, Any]) -> tuple[str, bool]:
        async with semaphore:
            return await download_image(session, record["url"])

    records = list(references.values())
    results = await asyncio.gather(*(download(record) for record in records))
    cached_count = 0
    downloaded_count = 0
    failed_count = 0
    for record, (local_url, was_cached) in zip(records, results, strict=True):
        if local_url.startswith("/api/images/"):
            cached_count += int(was_cached)
            downloaded_count += int(not was_cached)
            for item, key in record["targets"]:
                item[key] = local_url
        else:
            failed_count += 1

    await asyncio.to_thread(save_image_index)
    log_success(
        "图片处理完成: "
        f"新下载 {downloaded_count} 张, 已缓存 {cached_count} 张, 失败 {failed_count} 张"
    )


def prune_orphans(max_age_days: int | None = None) -> int:
    """Delete image files that are not in the index and older than the grace period."""
    days = config.IMAGE_ORPHAN_DAYS if max_age_days is None else max_age_days
    if days <= 0 or not config.IMAGE_CACHE_DIR.exists():
        return 0
    cutoff = time.time() - days * 86400
    referenced = set(image_index.values())
    removed = 0
    for date_dir in sorted(config.IMAGE_CACHE_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        for path in date_dir.iterdir():
            if not path.is_file():
                continue
            try:
                if path.stat().st_mtime >= cutoff:
                    continue
            except OSError:
                continue
            relative = path.relative_to(config.IMAGE_CACHE_DIR).as_posix()
            if relative in referenced:
                continue
            with suppress(OSError):
                path.unlink()
                removed += 1
        with suppress(OSError):
            if not any(date_dir.iterdir()):
                date_dir.rmdir()
    if removed:
        log_info(f"清理了 {removed} 个过期的孤立图片")
    return removed
