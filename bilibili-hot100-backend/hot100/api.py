"""FastAPI application: routes, lifespan and CORS."""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import config, images, state, storage
from .logs import log_info, log_manager
from .models import Hot100Response

MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _origin_allowed(origin: str | None) -> bool:
    return not origin or origin in config.ALLOWED_ORIGINS


def require_allowed_origin(request: Request) -> None:
    if not _origin_allowed(request.headers.get("origin")):
        raise HTTPException(status_code=403, detail="不允许的请求来源")


def _cache_response(message: str, from_cache: bool, response: Response) -> Hot100Response:
    if not state.cache["data"] or not state.cache["update_time"]:
        raise HTTPException(status_code=503, detail=state.cache["last_error"] or "数据尚未就绪")
    response.headers["Cache-Control"] = "no-store"
    return Hot100Response(
        code=0,
        message=message,
        data=state.cache["data"],
        update_time=state.iso_timestamp(state.cache["update_time"]),
        from_cache=from_cache,
        is_partial=bool(state.cache["is_partial"]),
        source=state.cache["source"] or "live",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await log_manager.start()
    images.rebuild_image_index()
    snapshot = storage.load_snapshot()
    if snapshot:
        state.apply_snapshot(snapshot)
    log_info("B站热门视频 API 服务启动")
    if config.PRELOAD:
        state.schedule_refresh()
    try:
        yield
    finally:
        await state.stop_refresh_task()
        await log_manager.stop()


app = FastAPI(title="B站热门视频 API", version=config.__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(config.ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/")
async def root():
    return {
        "message": "B站热门视频 API 服务运行中",
        "docs": "/docs",
        "version": config.__version__,
        "data_dir": str(config.DATA_ROOT),
    }


@app.get("/api/hot100", response_model=Hot100Response)
async def get_hot100(response: Response, force_refresh: bool = False):
    """Serve the cached snapshot; never start a crawl from a GET.

    ``force_refresh`` used to trigger a full crawl, which let any cross-site
    ``<img>`` keep the crawler busy. It is now rejected: use POST /api/refresh.
    """
    if force_refresh:
        raise HTTPException(
            status_code=400,
            detail="force_refresh 已移除，请使用 POST /api/refresh 触发刷新",
        )
    now = time.time()
    cache_valid = bool(
        state.cache["data"]
        and state.cache["update_time"]
        and now - state.cache["update_time"] < config.CACHE_TTL_SECONDS
    )
    if cache_valid:
        return _cache_response("success (from cache)", True, response)

    if state.cache["data"]:
        state.schedule_refresh()
        return _cache_response("stale cache; refresh started", True, response)

    task, _ = state.schedule_refresh()
    try:
        await task
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _cache_response("success", False, response)


@app.post("/api/refresh", status_code=202)
async def refresh_data(request: Request):
    require_allowed_origin(request)
    _, started = state.schedule_refresh()
    return {
        "code": 0,
        "message": "刷新任务已启动" if started else "刷新任务正在运行",
        "refresh_id": state.cache["refresh_id"],
        "is_updating": True,
    }


@app.get("/api/status")
async def get_status():
    return {
        "code": 0,
        "data": {
            "total_videos": len(state.cache["data"]),
            "update_time": (
                state.iso_timestamp(state.cache["update_time"])
                if state.cache["update_time"]
                else None
            ),
            "is_updating": state.cache["is_updating"],
            "refresh_id": state.cache["refresh_id"],
            "last_error": state.cache["last_error"],
            "is_partial": state.cache["is_partial"],
            "source": state.cache["source"],
            "snapshot_time": state.cache["snapshot_time"],
            "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
            "cached_images": len(images.image_files_by_name),
            "cached_urls": len(images.image_index),
            "data_dir": str(config.DATA_ROOT),
            "export_retention_days": config.EXPORT_RETENTION_DAYS,
        },
    }


@app.get("/api/images/{date}/{filename}")
async def get_image(date: str, filename: str):
    if not config.DATE_DIR_RE.fullmatch(date) or not config.IMAGE_ROUTE_RE.fullmatch(filename):
        raise HTTPException(status_code=404, detail="图片不存在")
    file_path = storage.image_path(date, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(
        file_path,
        media_type=MEDIA_TYPES[file_path.suffix[1:].lower()],
        headers={
            "Cache-Control": (f"public, max-age={config.IMAGE_CACHE_IMMUTABLE_MAX_AGE}, immutable")
        },
    )


@app.get("/api/exports")
async def get_exports(limit: int = config.EXPORT_LIST_LIMIT):
    listing = storage.list_exports(limit=max(1, min(limit, 200)))
    return {
        "code": 0,
        "data": listing["dates"],
        "total_dates": listing["total_dates"],
        "truncated": listing["truncated"],
        "retention_days": config.EXPORT_RETENTION_DAYS,
    }


@app.get("/api/exports/latest")
async def get_latest_export():
    latest = storage.latest_export()
    if not latest:
        raise HTTPException(status_code=404, detail="没有导出文件")
    latest_file, data = latest
    date_dir = latest_file.parent.name
    return {
        "code": 0,
        "data": data,
        "file_info": {
            "date": date_dir,
            "filename": latest_file.name,
            "path": f"/api/exports/{date_dir}/{latest_file.name}",
        },
    }


@app.get("/api/exports/{date}/{filename}")
async def get_export_file(date: str, filename: str):
    if not config.DATE_DIR_RE.fullmatch(date) or not config.EXPORT_FILE_RE.fullmatch(filename):
        raise HTTPException(status_code=404, detail="文件不存在")
    data = storage.read_export(date, filename)
    if data is None:
        raise HTTPException(status_code=404, detail="文件不存在")
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
