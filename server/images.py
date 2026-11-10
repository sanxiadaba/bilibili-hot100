"""封面 / 头像的本地缩略图缓存。

文件名是缩略图 URL 的 md5，扩展名按响应内容嗅探。启动时扫一遍目录就是全部
索引，不需要额外的 JSON 索引文件，也不会出现索引和磁盘对不上的情况。
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from contextlib import suppress

import aiohttp

from . import config
from .logs import log_info, log_success, log_warning

# md5 -> 文件名
files: dict[str, str] = {}
EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def normalize(url: str) -> str:
    return url.replace("http://", "https://", 1)


def thumb(url: str, size: tuple[int, int]) -> str:
    """B站图床支持 @宽w_高h_1c.webp，原图动辄几百 KB，缩略图只有几 KB。"""
    if not url:
        return ""
    url = normalize(url)
    if "@" in url:
        return url
    width, height = size
    return f"{url}@{width}w_{height}h_1c.webp"


def key(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def rebuild() -> None:
    files.clear()
    if not config.IMAGE_DIR.exists():
        return
    for path in config.IMAGE_DIR.iterdir():
        if path.is_file() and path.suffix[1:].lower() in EXTENSIONS:
            files[path.stem] = path.name
    if files:
        log_info(f"已加载 {len(files)} 张本地缩略图")


def local(url: str) -> str | None:
    name = files.get(key(url))
    return f"/img/{name}" if name else None


def _sniff(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"GIF8"):
        return "gif"
    return None


async def _download(session: aiohttp.ClientSession, url: str) -> None:
    if key(url) in files:
        return
    try:
        timeout = aiohttp.ClientTimeout(total=config.IMAGE_TIMEOUT)
        async with session.get(url, headers=config.IMAGE_HEADERS, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            data = await response.read()
    except (aiohttp.ClientError, TimeoutError, RuntimeError) as exc:
        log_warning(f"缩略图下载失败: {url[:70]} ({exc})")
        return

    extension = _sniff(data)
    if not extension:
        log_warning(f"响应不是图片，已跳过: {url[:70]}")
        return

    name = f"{key(url)}.{extension}"
    target = config.IMAGE_DIR / name
    try:
        await asyncio.to_thread(target.write_bytes, data)
    except OSError as exc:
        log_warning(f"缩略图写入失败: {exc}")
        return
    files[key(url)] = name


async def download_all(session: aiohttp.ClientSession, urls: set[str]) -> None:
    urls = {url for url in urls if url}
    missing = [url for url in urls if key(url) not in files]
    if not missing:
        return
    semaphore = asyncio.Semaphore(config.IMAGE_CONCURRENCY)

    async def run(url: str) -> None:
        async with semaphore:
            await _download(session, url)

    await asyncio.gather(*(run(url) for url in missing))
    ready = sum(1 for url in urls if key(url) in files)
    failed = len(urls) - ready
    log_success(f"缩略图就绪: 本地 {ready} 张, 新下载 {len(missing) - failed} 张, 失败 {failed} 张")


def display(url: str, size: tuple[int, int]) -> str:
    """返回 /img/... 或远程缩略图地址，两者都比原图小一个数量级。"""
    target = thumb(url, size)
    if not target:
        return ""
    return local(target) or target


def decorate(videos: list[dict]) -> list[dict]:
    """把 pic / face 换成缩略图地址，返回新对象，不改动快照里的原始数据。"""
    decorated: list[dict] = []
    for video in videos:
        item = {**video}
        item["pic"] = display(video.get("pic", ""), config.COVER_SIZE)
        owner = video.get("owner")
        if isinstance(owner, dict):
            item["owner"] = {**owner, "face": display(owner.get("face", ""), config.AVATAR_SIZE)}
        decorated.append(item)
    return decorated


def urls_for(videos: list[dict]) -> set[str]:
    urls: set[str] = set()
    for video in videos:
        urls.add(thumb(video.get("pic", ""), config.COVER_SIZE))
        owner = video.get("owner")
        if isinstance(owner, dict):
            urls.add(thumb(owner.get("face", ""), config.AVATAR_SIZE))
    return {url for url in urls if url}


def prune(keep_urls: set[str], max_age_days: int = 1) -> int:
    """删掉不在当前榜单里、且超过宽限期的旧图。"""
    keep = {key(url) for url in keep_urls}
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for stem, name in list(files.items()):
        if stem in keep:
            continue
        path = config.IMAGE_DIR / name
        try:
            if path.stat().st_mtime >= cutoff:
                continue
        except OSError:
            files.pop(stem, None)
            continue
        with suppress(OSError):
            path.unlink()
            removed += 1
        files.pop(stem, None)
    if removed:
        log_info(f"清理了 {removed} 张过期缩略图")
    return removed
