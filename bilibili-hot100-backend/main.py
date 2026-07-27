"""FastAPI service for the Bilibili popular-video dashboard."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from collections import deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import aiofiles
import aiohttp
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


class CrawlError(RuntimeError):
    """Raised when a complete, valid TOP 100 snapshot cannot be produced."""


class VideoStat(BaseModel):
    view: int
    danmaku: int
    reply: int
    favorite: int
    coin: int
    share: int
    like: int


class VideoOwner(BaseModel):
    mid: int
    name: str
    face: str


class VideoItem(BaseModel):
    aid: int
    bvid: str
    title: str
    pic: str
    duration: int
    pubdate: int
    owner: VideoOwner
    stat: VideoStat
    tname: str
    rank: int
    rcmd_reason: Optional[dict] = None


class Hot100Response(BaseModel):
    code: int
    message: str
    data: List[VideoItem]
    update_time: str
    from_cache: bool


class LogManager:
    def __init__(self, max_size: int = 500):
        self.logs: deque[dict] = deque(maxlen=max_size)
        self.websockets: List[WebSocket] = []
        self.lock = asyncio.Lock()
        self.queue: Optional[asyncio.Queue[dict]] = None
        self.worker: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        self.queue = asyncio.Queue(maxsize=1000)
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
            results = await asyncio.gather(
                *(ws.send_json({"type": "log", "data": entry}) for ws in connections),
                return_exceptions=True,
            )
            disconnected = [
                ws for ws, result in zip(connections, results) if isinstance(result, Exception)
            ]
            if disconnected:
                async with self.lock:
                    self.websockets = [ws for ws in self.websockets if ws not in disconnected]

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.websockets.append(websocket)
            history = list(self.logs)
        for entry in history:
            await websocket.send_json({"type": "log", "data": entry})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.lock:
            if websocket in self.websockets:
                self.websockets.remove(websocket)

    def get_logs(self) -> List[dict]:
        return list(self.logs)

    def clear(self) -> None:
        self.logs.clear()


log_manager = LogManager()

cache: Dict[str, Any] = {
    "data": [],
    "update_time": None,
    "is_updating": False,
    "refresh_id": None,
    "last_error": None,
}
refresh_lock = asyncio.Lock()
current_refresh_task: Optional[asyncio.Task[None]] = None

BACKEND_DIR = Path(__file__).resolve().parent
DATA_ROOT = Path(os.getenv("BILIBILI_DATA_DIR", str(BACKEND_DIR))).resolve()
CACHE_DIR = DATA_ROOT / "cache"
IMAGE_CACHE_DIR = CACHE_DIR / "images"
DATA_EXPORT_DIR = DATA_ROOT / "data_exports"
IMAGE_INDEX_FILE = CACHE_DIR / "downloaded_urls.json"
for directory in (CACHE_DIR, IMAGE_CACHE_DIR, DATA_EXPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DEFAULT_ORIGINS = "http://127.0.0.1:3000,http://localhost:3000"
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv("BILIBILI_ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
}

BILIBILI_API = "https://api.bilibili.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

image_index: Dict[str, str] = {}
image_files_by_name: Dict[str, Path] = {}
IMAGE_ROUTE_RE = re.compile(r"^[0-9a-f]{32}\.(?:jpg|jpeg|png|webp|gif)$")
EXPORT_FILE_RE = re.compile(r"^\d{6}\.json$")


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


def normalize_image_url(url: str) -> str:
    return url.replace("http://", "https://", 1)


def _image_extension(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "gif"} else "jpg"


def _image_filename(url: str) -> str:
    normalized = normalize_image_url(url)
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return f"{digest}.{_image_extension(normalized)}"


def _safe_child(root: Path, relative_path: str) -> Optional[Path]:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def rebuild_image_index() -> None:
    """Build a constant-time URL-to-file index and migrate the legacy URL list."""
    image_index.clear()
    image_files_by_name.clear()
    for path in IMAGE_CACHE_DIR.glob("*/*"):
        if path.is_file():
            image_files_by_name[path.name] = path

    raw: Any = {}
    if IMAGE_INDEX_FILE.exists():
        try:
            raw = json.loads(IMAGE_INDEX_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_warning(f"图片缓存索引读取失败，将重建: {exc}")

    if isinstance(raw, dict):
        for url, relative_path in raw.items():
            if not isinstance(url, str) or not isinstance(relative_path, str):
                continue
            path = _safe_child(IMAGE_CACHE_DIR, relative_path)
            if path and path.is_file():
                image_index[normalize_image_url(url)] = relative_path.replace("\\", "/")
    elif isinstance(raw, list):
        for url in raw:
            if isinstance(url, str):
                _resolve_cached_image(url)

    if image_index:
        log_info(f"已加载 {len(image_index)} 个有效图片缓存")


def _resolve_cached_image(url: str) -> Optional[str]:
    normalized = normalize_image_url(url)
    relative_path = image_index.get(normalized)
    if relative_path:
        path = _safe_child(IMAGE_CACHE_DIR, relative_path)
        if path and path.is_file():
            return f"/api/images/{relative_path.replace(os.sep, '/')}"
        image_index.pop(normalized, None)

    filenames = {_image_filename(url)}
    original_digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    filenames.add(f"{original_digest}.{_image_extension(url)}")
    for filename in filenames:
        path = image_files_by_name.get(filename)
        if path and path.is_file():
            relative = path.relative_to(IMAGE_CACHE_DIR).as_posix()
            image_index[normalized] = relative
            return f"/api/images/{relative}"
    return None


def _save_image_index() -> None:
    IMAGE_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = IMAGE_INDEX_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(image_index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, IMAGE_INDEX_FILE)


async def download_image(session: aiohttp.ClientSession, url: str) -> tuple[str, bool]:
    cached_url = _resolve_cached_image(url)
    if cached_url:
        return cached_url, True

    normalized = normalize_image_url(url)
    date = datetime.now().strftime("%Y%m%d")
    date_dir = IMAGE_CACHE_DIR / date
    date_dir.mkdir(parents=True, exist_ok=True)
    filename = _image_filename(normalized)
    target = date_dir / filename
    temporary = target.with_suffix(target.suffix + ".tmp")

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(normalized, headers=HEADERS, timeout=timeout) as response:
            if response.status != 200:
                raise CrawlError(f"HTTP {response.status}")
            content = await response.read()
            if not content:
                raise CrawlError("响应内容为空")
        async with aiofiles.open(temporary, "wb") as file:
            await file.write(content)
        await asyncio.to_thread(os.replace, temporary, target)
        relative = target.relative_to(IMAGE_CACHE_DIR).as_posix()
        image_index[normalized] = relative
        image_files_by_name[filename] = target
        return f"/api/images/{relative}", False
    except Exception as exc:
        with suppress(OSError):
            temporary.unlink()
        log_warning(f"图片下载失败: {url[:60]} ({exc})")
        return url, False


def get_export_dir_by_date() -> Path:
    date_dir = DATA_EXPORT_DIR / datetime.now().strftime("%Y%m%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir


async def export_data_to_json(videos: List[dict]) -> Optional[Path]:
    if not videos:
        return None
    now = datetime.now()
    file_path = get_export_dir_by_date() / f"{now:%H%M%S}.json"
    payload = {
        "export_time": now.isoformat(),
        "date": f"{now:%Y-%m-%d}",
        "time": f"{now:%H:%M:%S}",
        "total": len(videos),
        "videos": videos,
    }
    temporary = file_path.with_suffix(".tmp")
    async with aiofiles.open(temporary, "w", encoding="utf-8") as file:
        await file.write(json.dumps(payload, ensure_ascii=False, indent=2))
    await asyncio.to_thread(os.replace, temporary, file_path)
    return file_path


async def fetch_page(
    session: aiohttp.ClientSession, page: int, page_size: int = 50
) -> List[dict]:
    url = f"{BILIBILI_API}/x/web-interface/popular"
    params = {"ps": page_size, "pn": page}
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.get(url, params=params, headers=HEADERS, timeout=timeout) as response:
            if response.status != 200:
                raise CrawlError(f"第 {page} 页 HTTP {response.status}")
            payload = await response.json()
    except asyncio.TimeoutError as exc:
        raise CrawlError(f"第 {page} 页请求超时") from exc
    except aiohttp.ClientError as exc:
        raise CrawlError(f"第 {page} 页网络异常: {exc}") from exc

    if payload.get("code") != 0:
        raise CrawlError(f"第 {page} 页 API 错误: {payload.get('message', 'unknown')}")
    videos = payload.get("data", {}).get("list")
    if not isinstance(videos, list) or len(videos) != page_size:
        actual = len(videos) if isinstance(videos, list) else 0
        raise CrawlError(f"第 {page} 页数据不完整: 期望 {page_size}，实际 {actual}")
    log_success(f"第 {page} 页获取成功: {len(videos)} 个视频")
    return videos


def validate_video_batch(videos: List[dict]) -> None:
    if len(videos) != 100:
        raise CrawlError(f"热门数据不完整: 期望 100，实际 {len(videos)}")
    bvids = [video.get("bvid") for video in videos]
    if len(set(bvids)) != 100 or None in bvids:
        raise CrawlError("热门数据包含缺失或重复的 BV 号")
    for rank, video in enumerate(videos, start=1):
        video["rank"] = rank
        try:
            VideoItem.model_validate(video)
        except Exception as exc:
            raise CrawlError(f"第 {rank} 条视频字段无效: {exc}") from exc


async def cache_video_images(session: aiohttp.ClientSession, videos: List[dict]) -> None:
    references: Dict[str, Dict[str, Any]] = {}
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

    semaphore = asyncio.Semaphore(10)

    async def download(record: Dict[str, Any]) -> tuple[str, bool]:
        async with semaphore:
            return await download_image(session, record["url"])

    records = list(references.values())
    results = await asyncio.gather(*(download(record) for record in records))
    cached_count = 0
    downloaded_count = 0
    failed_count = 0
    for record, (local_url, was_cached) in zip(records, results):
        if local_url.startswith("/api/images/"):
            cached_count += int(was_cached)
            downloaded_count += int(not was_cached)
            for item, key in record["targets"]:
                item[key] = local_url
        else:
            failed_count += 1

    await asyncio.to_thread(_save_image_index)
    log_success(
        "图片处理完成: "
        f"新下载 {downloaded_count} 张, 已缓存 {cached_count} 张, 失败 {failed_count} 张"
    )


async def crawl_hot100() -> List[dict]:
    log_info("开始爬取 B站热门视频 TOP 100")
    started = time.monotonic()
    async with aiohttp.ClientSession() as session:
        pages = await asyncio.gather(fetch_page(session, 1), fetch_page(session, 2))
        videos = [video for page in pages for video in page]
        validate_video_batch(videos)
        await cache_video_images(session, videos)
    export_path = await export_data_to_json(videos)
    log_success(f"数据爬取完成: 100 个视频, 耗时 {time.monotonic() - started:.2f} 秒")
    if export_path:
        log_info(f"JSON 数据已导出: {export_path}")
    return videos


async def _run_refresh(refresh_id: str) -> None:
    async with refresh_lock:
        try:
            videos = await crawl_hot100()
            timestamp = time.time()
            cache["data"] = videos
            cache["update_time"] = timestamp
            cache["last_error"] = None
            log_success(f"刷新完成: {len(videos)} 个视频")
        except Exception as exc:
            cache["last_error"] = str(exc)
            log_error(f"刷新失败，保留现有缓存: {exc}")
            raise
        finally:
            if cache["refresh_id"] == refresh_id:
                cache["is_updating"] = False


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


def _cache_response(message: str, from_cache: bool) -> Hot100Response:
    if not cache["data"] or not cache["update_time"]:
        raise HTTPException(status_code=503, detail=cache["last_error"] or "数据尚未就绪")
    return Hot100Response(
        code=0,
        message=message,
        data=cache["data"],
        update_time=datetime.fromtimestamp(cache["update_time"]).isoformat(),
        from_cache=from_cache,
    )


def _origin_allowed(origin: Optional[str]) -> bool:
    return not origin or origin in ALLOWED_ORIGINS


def require_allowed_origin(request: Request) -> None:
    if not _origin_allowed(request.headers.get("origin")):
        raise HTTPException(status_code=403, detail="不允许的请求来源")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await log_manager.start()
    rebuild_image_index()
    log_info("B站热门视频 API 服务启动")
    if os.getenv("BILIBILI_PRELOAD", "1").lower() not in {"0", "false", "no"}:
        schedule_refresh()
    try:
        yield
    finally:
        if current_refresh_task and not current_refresh_task.done():
            current_refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await current_refresh_task
        await log_manager.stop()


app = FastAPI(title="B站热门视频 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    return {"message": "B站热门视频 API 服务运行中", "docs": "/docs", "version": "2.0.0"}


@app.get("/api/hot100", response_model=Hot100Response)
async def get_hot100(force_refresh: bool = False):
    now = time.time()
    cache_valid = bool(
        cache["data"]
        and cache["update_time"]
        and now - cache["update_time"] < 300
        and not force_refresh
    )
    if cache_valid:
        return _cache_response("success (from cache)", True)

    if force_refresh:
        task, _ = schedule_refresh()
        try:
            await task
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return _cache_response("success", False)

    if cache["data"]:
        schedule_refresh()
        return _cache_response("stale cache; refresh started", True)

    task, _ = schedule_refresh()
    try:
        await task
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _cache_response("success", False)


@app.post("/api/refresh", status_code=202)
async def refresh_data(request: Request):
    require_allowed_origin(request)
    _, started = schedule_refresh()
    return {
        "code": 0,
        "message": "刷新任务已启动" if started else "刷新任务正在运行",
        "refresh_id": cache["refresh_id"],
        "is_updating": True,
    }


@app.get("/api/status")
async def get_status():
    return {
        "code": 0,
        "data": {
            "total_videos": len(cache["data"]),
            "update_time": (
                datetime.fromtimestamp(cache["update_time"]).isoformat()
                if cache["update_time"]
                else None
            ),
            "is_updating": cache["is_updating"],
            "refresh_id": cache["refresh_id"],
            "last_error": cache["last_error"],
            "cached_images": len(image_files_by_name),
            "cached_urls": len(image_index),
        },
    }


@app.get("/api/images/{date}/{filename}")
async def get_image(date: str, filename: str):
    if not re.fullmatch(r"\d{8}", date) or not IMAGE_ROUTE_RE.fullmatch(filename):
        raise HTTPException(status_code=404, detail="图片不存在")
    file_path = _safe_child(IMAGE_CACHE_DIR, f"{date}/{filename}")
    if not file_path or not file_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    return FileResponse(file_path, media_type=media_types[file_path.suffix[1:].lower()])


@app.get("/api/exports")
async def get_exports():
    exports = []
    for date_dir in sorted(DATA_EXPORT_DIR.iterdir(), reverse=True):
        if not date_dir.is_dir() or not re.fullmatch(r"\d{8}", date_dir.name):
            continue
        files = []
        for json_file in sorted(date_dir.glob("*.json"), reverse=True):
            stat = json_file.stat()
            files.append(
                {
                    "filename": json_file.name,
                    "time": json_file.stem,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "url": f"/api/exports/{date_dir.name}/{json_file.name}",
                }
            )
        if files:
            exports.append(
                {
                    "date": date_dir.name,
                    "formatted_date": (
                        f"{date_dir.name[:4]}-{date_dir.name[4:6]}-{date_dir.name[6:]}"
                    ),
                    "count": len(files),
                    "files": files,
                }
            )
    return {"code": 0, "data": exports}


@app.get("/api/exports/latest")
async def get_latest_export():
    date_dirs = sorted(
        [path for path in DATA_EXPORT_DIR.iterdir() if re.fullmatch(r"\d{8}", path.name)],
        reverse=True,
    )
    for date_dir in date_dirs:
        json_files = sorted(date_dir.glob("*.json"), reverse=True)
        if json_files:
            latest_file = json_files[0]
            async with aiofiles.open(latest_file, "r", encoding="utf-8") as file:
                data = json.loads(await file.read())
            return {
                "code": 0,
                "data": data,
                "file_info": {
                    "date": date_dir.name,
                    "filename": latest_file.name,
                    "path": f"/api/exports/{date_dir.name}/{latest_file.name}",
                },
            }
    raise HTTPException(status_code=404, detail="没有导出文件")


@app.get("/api/exports/{date}/{filename}")
async def get_export_file(date: str, filename: str):
    if not re.fullmatch(r"\d{8}", date) or not EXPORT_FILE_RE.fullmatch(filename):
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = _safe_child(DATA_EXPORT_DIR, f"{date}/{filename}")
    if not file_path or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
        data = json.loads(await file.read())
    return {"code": 0, "data": data}


@app.websocket("/api/logs/ws")
async def websocket_logs(websocket: WebSocket):
    if not _origin_allowed(websocket.headers.get("origin")):
        await websocket.close(code=1008)
        return
    await log_manager.connect(websocket)
    log_info(f"新的日志客户端连接，当前连接数: {len(log_manager.websockets)}")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("action") == "clear":
                log_manager.clear()
                await websocket.send_json({"type": "cleared"})
    except WebSocketDisconnect:
        pass
    finally:
        await log_manager.disconnect(websocket)


@app.get("/api/logs")
async def get_logs():
    return {"code": 0, "data": log_manager.get_logs()}


@app.delete("/api/logs")
async def clear_logs(request: Request):
    require_allowed_origin(request)
    log_manager.clear()
    return {"code": 0, "message": "日志已清空"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("BILIBILI_HOST", "127.0.0.1"),
        port=int(os.getenv("BILIBILI_PORT", "8000")),
    )
