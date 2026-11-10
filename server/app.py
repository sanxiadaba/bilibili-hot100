"""FastAPI 应用：API、缩略图、日志推送和前端静态文件。"""

from __future__ import annotations

import json
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config, images, store
from .logs import log_manager
from .models import Hot100Response

MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}
IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.(?:jpg|jpeg|png|webp|gif)$")


def _same_origin(headers) -> bool:
    """只允许本机页面触发写操作；忽略端口，方便 Vite 开发服务器代理。"""
    origin = headers.get("origin")
    if not origin:
        return True
    host = headers.get("host", "")
    request_host = urlsplit(f"//{host}").hostname
    return urlsplit(origin).hostname == request_host


def require_same_origin(request: Request) -> None:
    if not _same_origin(request.headers):
        raise HTTPException(status_code=403, detail="不允许的请求来源")


@asynccontextmanager
async def lifespan(_: FastAPI):
    config.ensure_dirs()
    await log_manager.start()
    images.rebuild()
    store.startup()
    if config.PRELOAD and (not store.cache["videos"] or store.is_stale()):
        store.schedule()
    try:
        yield
    finally:
        await store.stop()
        await log_manager.stop()


app = FastAPI(title="B站热门视频", version="3.0.0", lifespan=lifespan)


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/hot100", response_model=Hot100Response)
async def get_hot100() -> Hot100Response:
    """只读内存缓存；数据过期时顺手在后台刷新，本次请求不等它。"""
    if not store.cache["videos"]:
        raise HTTPException(status_code=503, detail="正在抓取，请稍候")
    if store.is_stale():
        store.schedule()
    return Hot100Response(
        data=images.decorate(store.cache["videos"]),
        update_time=store.iso_timestamp(store.cache["update_time"]),
        is_partial=bool(store.cache["is_partial"]),
        source=store.cache["source"] or "live",
        is_stale=store.is_stale(),
        is_updating=bool(store.cache["is_updating"]),
    )


@app.post("/api/refresh", status_code=202)
async def refresh(request: Request) -> dict:
    require_same_origin(request)
    started = store.schedule()
    return {"started": started}


@app.get("/api/status")
async def get_status() -> dict:
    return store.status()


@app.get("/api/export")
async def export_data() -> Response:
    """导出当前缓存，图片保留 B站原始地址，拿到别处也能用。"""
    videos = store.cache["videos"]
    if not videos:
        raise HTTPException(status_code=404, detail="还没有数据")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {
        "export_time": store.iso_timestamp(time.time()),
        "update_time": store.iso_timestamp(store.cache["update_time"]),
        "is_partial": bool(store.cache["is_partial"]),
        "total": len(videos),
        "videos": videos,
    }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="bilibili-hot100-{stamp}.json"'},
    )


@app.get("/img/{filename}")
async def get_image(filename: str) -> FileResponse:
    if not IMAGE_NAME.fullmatch(filename):
        raise HTTPException(status_code=404, detail="图片不存在")
    extension = filename.rsplit(".", 1)[-1].lower()
    path = config.IMAGE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[extension],
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/api/logs")
async def get_logs() -> dict:
    return {"data": list(log_manager.logs)}


@app.delete("/api/logs")
async def clear_logs(request: Request) -> dict:
    require_same_origin(request)
    log_manager.clear()
    return {"ok": True}


@app.websocket("/api/logs/ws")
async def logs_socket(websocket: WebSocket) -> None:
    if not _same_origin(websocket.headers):
        await websocket.close(code=1008)
        return
    await log_manager.connect(websocket)
    try:
        while True:
            message = json.loads(await websocket.receive_text())
            if message.get("action") == "clear":
                log_manager.clear()
                await websocket.send_json({"type": "cleared"})
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        log_manager.disconnect(websocket)


if config.WEB_DIST.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(config.WEB_DIST), html=True),
        name="web",
    )
else:

    @app.get("/", include_in_schema=False)
    async def missing_web() -> HTMLResponse:
        return HTMLResponse(
            "<h1>前端尚未构建</h1><p>运行 <code>python run.py</code> 会自动构建。</p>",
            status_code=503,
        )
