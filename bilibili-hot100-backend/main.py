"""
B站热门视频 TOP 100 后端服务
使用 FastAPI + 异步爬虫实现实时数据获取
支持 WebSocket 实时日志推送
图片按日期分类存储，避免重复下载
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Set
from pathlib import Path
from collections import deque

import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="B站热门视频 API", version="1.2.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
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

class LogEntry(BaseModel):
    time: str
    level: str
    message: str

# 日志管理器
class LogManager:
    def __init__(self, max_size: int = 500):
        self.logs: deque = deque(maxlen=max_size)
        self.websockets: List[WebSocket] = []
        self.lock = asyncio.Lock()
    
    def add_log(self, level: str, message: str):
        """添加日志条目"""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "level": level,
            "message": message
        }
        self.logs.append(entry)
        # 异步推送日志到所有WebSocket客户端
        asyncio.create_task(self.broadcast(entry))
    
    async def broadcast(self, entry: dict):
        """广播日志到所有连接的WebSocket客户端"""
        disconnected = []
        for ws in self.websockets:
            try:
                await ws.send_json({"type": "log", "data": entry})
            except:
                disconnected.append(ws)
        
        # 清理断开的连接
        for ws in disconnected:
            if ws in self.websockets:
                self.websockets.remove(ws)
    
    async def connect(self, websocket: WebSocket):
        """连接WebSocket"""
        await websocket.accept()
        async with self.lock:
            self.websockets.append(websocket)
        # 发送历史日志
        for entry in self.logs:
            await websocket.send_json({"type": "log", "data": entry})
    
    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket"""
        async with self.lock:
            if websocket in self.websockets:
                self.websockets.remove(websocket)
    
    def get_logs(self) -> List[dict]:
        """获取所有日志"""
        return list(self.logs)
    
    def clear(self):
        """清空日志"""
        self.logs.clear()

# 全局日志管理器
log_manager = LogManager()

# 全局缓存
cache = {
    "data": [],
    "update_time": None,
    "is_updating": False
}

# JSON 数据导出目录
DATA_EXPORT_DIR = Path(__file__).parent / "data_exports"
DATA_EXPORT_DIR.mkdir(exist_ok=True)

def get_export_dir_by_date() -> Path:
    """获取按日期分类的数据导出目录"""
    today = datetime.now().strftime("%Y%m%d")
    date_dir = DATA_EXPORT_DIR / today
    date_dir.mkdir(exist_ok=True)
    return date_dir

def get_export_filename() -> str:
    """生成导出文件名（包含时间戳）"""
    now = datetime.now()
    return now.strftime("%H%M%S") + ".json"

async def export_data_to_json(videos: List[dict]):
    """导出数据到 JSON 文件，按日期时间分类"""
    if not videos:
        return None
    
    # 获取导出目录
    export_dir = get_export_dir_by_date()
    filename = get_export_filename()
    file_path = export_dir / filename
    
    # 准备导出数据
    export_data = {
        "export_time": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "total": len(videos),
        "videos": videos
    }
    
    # 写入 JSON 文件
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))
    
    log_success(f"数据已导出到: {file_path}")
    return file_path

# 已下载图片URL集合（用于去重，持久化到磁盘避免重启后重复下载）
downloaded_urls: Set[str] = set()
URLS_CACHE_FILE = None  # 延迟初始化

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
IMAGE_CACHE_DIR = CACHE_DIR / "images"
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


def _get_urls_cache_file() -> Path:
    """延迟初始化_urls缓存文件路径"""
    global URLS_CACHE_FILE
    if URLS_CACHE_FILE is None:
        URLS_CACHE_FILE = CACHE_DIR / "downloaded_urls.json"
    return URLS_CACHE_FILE


def _save_downloaded_urls():
    """将已下载URL集合持久化到JSON文件"""
    try:
        with open(_get_urls_cache_file(), 'w', encoding='utf-8') as f:
            json.dump(list(downloaded_urls), f, ensure_ascii=False)
    except Exception:
        pass  # 写入失败不影响主流程


def _load_downloaded_urls():
    """从JSON文件加载已下载URL集合"""
    cache_file = _get_urls_cache_file()
    if not cache_file.exists():
        return
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            urls = json.load(f)
        downloaded_urls.update(urls)
        if downloaded_urls:
            log_info(f"已加载 {len(downloaded_urls)} 个已下载图片URL（持久化缓存）")
    except Exception:
        pass


def rebuild_downloaded_urls():
    """启动时加载URL持久化文件，恢复已下载URL集合"""
    _load_downloaded_urls()

# B站 API 配置
BILIBILI_API = "https://api.bilibili.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

def log_info(message: str):
    """记录信息日志"""
    log_manager.add_log("INFO", message)

def log_success(message: str):
    """记录成功日志"""
    log_manager.add_log("SUCCESS", message)

def log_warning(message: str):
    """记录警告日志"""
    log_manager.add_log("WARNING", message)

def log_error(message: str):
    """记录错误日志"""
    log_manager.add_log("ERROR", message)

def log_debug(message: str):
    """记录调试日志"""
    log_manager.add_log("DEBUG", message)

def get_image_dir_by_date() -> Path:
    """获取按日期分类的图片目录"""
    today = datetime.now().strftime("%Y%m%d")
    date_dir = IMAGE_CACHE_DIR / today
    date_dir.mkdir(exist_ok=True)
    return date_dir

def get_image_path(url: str) -> tuple[Path, str]:
    """
    获取图片存储路径和URL
    返回: (文件路径, 访问URL)
    """
    if not url:
        return None, ""
    
    # 生成URL的hash作为文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = url.split('.')[-1].split('@')[0] if '.' in url else 'jpg'
    if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
        ext = 'jpg'
    
    # 查找是否已存在（遍历所有日期目录）
    for date_dir in IMAGE_CACHE_DIR.iterdir():
        if date_dir.is_dir():
            for img_file in date_dir.glob(f"{url_hash}.{ext}"):
                if img_file.exists():
                    # 已存在，返回现有路径
                    relative_path = f"{date_dir.name}/{img_file.name}"
                    return img_file, f"/api/images/{relative_path}"
    
    # 不存在，创建新路径（按日期分类）
    date_dir = get_image_dir_by_date()
    filename = f"{url_hash}.{ext}"
    file_path = date_dir / filename
    relative_path = f"{date_dir.name}/{filename}"
    
    return file_path, f"/api/images/{relative_path}"

async def download_image(session: aiohttp.ClientSession, url: str) -> str:
    """
    下载图片并缓存，返回本地URL
    使用URL hash去重，避免重复下载
    """
    if not url:
        return ""
    
    # 标准化URL（移除协议差异）
    normalized_url = url.replace("http://", "https://")
    
    # 检查是否已下载（内存集合命中即跳过）
    if normalized_url in downloaded_urls:
        log_debug(f"图片已缓存(跳过): {url[:50]}...")
        _, local_url = get_image_path(url)
        return local_url

    # 获取存储路径
    file_path, local_url = get_image_path(url)

    # 如果文件已存在，直接返回
    if file_path and file_path.exists():
        downloaded_urls.add(normalized_url)
        _save_downloaded_urls()
        return local_url
    
    try:
        # 下载图片
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                content = await resp.read()
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                downloaded_urls.add(normalized_url)
                _save_downloaded_urls()
                log_debug(f"图片下载成功: {url[:50]}...")
                return local_url
            else:
                log_warning(f"图片下载失败 HTTP {resp.status}: {url[:50]}...")
    except Exception as e:
        log_warning(f"图片下载失败: {url[:50]}... 错误: {str(e)}")
    
    return url  # 失败返回原URL

async def fetch_page(session: aiohttp.ClientSession, page: int, page_size: int = 50) -> List[dict]:
    """获取单页热门视频数据"""
    url = f"{BILIBILI_API}/x/web-interface/popular"
    params = {"ps": page_size, "pn": page}
    
    log_debug(f"请求第 {page} 页数据...")
    
    try:
        async with session.get(url, params=params, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            log_debug(f"第 {page} 页响应状态: {resp.status}")
            if resp.status != 200:
                log_error(f"请求第 {page} 页失败: HTTP {resp.status}")
                return []
            data = await resp.json()
            if data.get("code") == 0:
                videos = data.get("data", {}).get("list", [])
                log_success(f"第 {page} 页获取成功: {len(videos)} 个视频")
                return videos
            else:
                log_error(f"API 错误: {data.get('message')}")
                return []
    except asyncio.TimeoutError:
        log_error(f"请求第 {page} 页超时")
        return []
    except Exception as e:
        log_error(f"请求第 {page} 页异常: {str(e)}")
        return []

async def crawl_hot100() -> List[dict]:
    """爬取热门视频 TOP 100"""
    log_info("=" * 50)
    log_info("开始爬取 B站热门视频 TOP 100")
    log_info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_info("=" * 50)
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        # 并发获取两页数据
        log_info("并发请求第1页和第2页数据...")
        tasks = [
            fetch_page(session, 1, 50),
            fetch_page(session, 2, 50)
        ]
        results = await asyncio.gather(*tasks)
        
        all_videos = []
        for page_videos in results:
            all_videos.extend(page_videos)
        
        # 只取前100个
        all_videos = all_videos[:100]
        
        log_info(f"共获取到 {len(all_videos)} 个视频")
        
        if not all_videos:
            log_error("没有获取到任何视频数据")
            return []
        
        log_info("开始下载图片资源...")
        
        # 收集所有唯一的图片URL
        unique_image_urls = set()
        image_mappings = []  # (item, key, url)
        
        for i, video in enumerate(all_videos):
            video['rank'] = i + 1
            # 视频封面
            if video.get('pic'):
                url = video['pic']
                normalized = url.replace("http://", "https://")
                if normalized not in unique_image_urls:
                    unique_image_urls.add(normalized)
                    image_mappings.append((video, 'pic', url))
            # UP主头像
            if video.get('owner', {}).get('face'):
                url = video['owner']['face']
                normalized = url.replace("http://", "https://")
                if normalized not in unique_image_urls:
                    unique_image_urls.add(normalized)
                    image_mappings.append((video['owner'], 'face', url))
        
        log_info(f"需要下载 {len(image_mappings)} 张唯一图片 (已去重)")
        
        # 批量下载图片（限制并发数）
        semaphore = asyncio.Semaphore(10)
        downloaded = 0
        skipped = 0
        failed = 0
        
        async def download_with_limit(item, key, url):
            nonlocal downloaded, skipped, failed
            async with semaphore:
                normalized = url.replace("http://", "https://")
                if normalized in downloaded_urls:
                    # 已下载过，直接获取路径
                    _, local_url = get_image_path(url)
                    if local_url:
                        skipped += 1
                        return item, key, local_url
                
                local_url = await download_image(session, url)
                if local_url.startswith('/api/images/'):
                    downloaded += 1
                else:
                    failed += 1
                return item, key, local_url
        
        download_tasks = [download_with_limit(item, key, url) for item, key, url in image_mappings]
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # 更新URL为本地缓存地址
        for result in download_results:
            if isinstance(result, Exception):
                log_error(f"图片下载异常: {str(result)}")
                continue
            item, key, local_url = result
            if local_url:
                item[key] = local_url
        
        elapsed = time.time() - start_time
        log_success(f"图片处理完成: 新下载 {downloaded} 张, 已缓存跳过 {skipped} 张, 失败 {failed} 张")
        log_success(f"数据爬取完成! 共 {len(all_videos)} 个视频, 耗时 {elapsed:.2f} 秒")
        
        # 导出数据到 JSON 文件
        export_path = await export_data_to_json(all_videos)
        if export_path:
            log_success(f"JSON 数据已导出: {export_path}")
        
        log_info("=" * 50)
        
        return all_videos

@app.get("/")
async def root():
    return {"message": "B站热门视频 API 服务运行中", "docs": "/docs", "version": "1.2.0"}

@app.get("/api/hot100", response_model=Hot100Response)
async def get_hot100(force_refresh: bool = False):
    """
    获取热门视频 TOP 100
    - force_refresh: 是否强制刷新数据
    """
    global cache
    
    log_info(f"收到数据请求 (force_refresh={force_refresh})")
    
    # 检查缓存是否有效（5分钟内）
    cache_valid = (
        cache["data"] and 
        cache["update_time"] and 
        (time.time() - cache["update_time"] < 300) and  # 5分钟缓存
        not force_refresh
    )
    
    if cache_valid:
        log_info("返回缓存数据")
        return Hot100Response(
            code=0,
            message="success (from cache)",
            data=cache["data"],
            update_time=datetime.fromtimestamp(cache["update_time"]).isoformat(),
            from_cache=True
        )
    
    # 如果正在更新，返回缓存数据
    if cache["is_updating"] and cache["data"]:
        log_info("正在更新中，返回缓存数据")
        return Hot100Response(
            code=0,
            message="updating, returning cached data",
            data=cache["data"],
            update_time=datetime.fromtimestamp(cache["update_time"]).isoformat() if cache["update_time"] else None,
            from_cache=True
        )
    
    # 爬取新数据
    try:
        cache["is_updating"] = True
        log_info("开始爬取新数据...")
        videos = await crawl_hot100()
        cache["data"] = videos
        cache["update_time"] = time.time()
        cache["is_updating"] = False
        
        log_success(f"数据更新完成: {len(videos)} 个视频")
        
        return Hot100Response(
            code=0,
            message="success",
            data=videos,
            update_time=datetime.now().isoformat(),
            from_cache=False
        )
    except Exception as e:
        cache["is_updating"] = False
        log_error(f"爬取数据失败: {str(e)}")
        # 如果有缓存，返回缓存数据
        if cache["data"]:
            log_warning("返回旧缓存数据")
            return Hot100Response(
                code=0,
                message=f"error: {str(e)}, returning cached data",
                data=cache["data"],
                update_time=datetime.fromtimestamp(cache["update_time"]).isoformat() if cache["update_time"] else None,
                from_cache=True
            )
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """后台刷新数据"""
    global cache
    
    if cache["is_updating"]:
        log_warning("刷新请求被拒绝: 正在更新中")
        return {"code": -1, "message": "正在更新中，请稍后再试"}
    
    log_info("收到刷新请求，启动后台刷新任务")
    
    async def do_refresh():
        try:
            cache["is_updating"] = True
            log_info("后台刷新任务开始...")
            videos = await crawl_hot100()
            cache["data"] = videos
            cache["update_time"] = time.time()
            log_success(f"后台刷新完成: {len(videos)} 个视频")
        except Exception as e:
            log_error(f"后台刷新失败: {str(e)}")
        finally:
            cache["is_updating"] = False
    
    # 在后台执行刷新
    asyncio.create_task(do_refresh())
    
    return {"code": 0, "message": "刷新任务已启动"}

@app.get("/api/images/{date}/{filename}")
async def get_image(date: str, filename: str):
    """获取缓存的图片（按日期分类）"""
    file_path = IMAGE_CACHE_DIR / date / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 根据文件扩展名设置 content-type
    ext = filename.split('.')[-1].lower()
    content_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif'
    }
    content_type = content_type_map.get(ext, 'image/jpeg')
    
    return FileResponse(file_path, media_type=content_type)

@app.get("/api/status")
async def get_status():
    """获取服务状态"""
    # 计算图片总数
    total_images = 0
    for date_dir in IMAGE_CACHE_DIR.iterdir():
        if date_dir.is_dir():
            total_images += len(list(date_dir.glob("*")))
    
    return {
        "code": 0,
        "data": {
            "total_videos": len(cache["data"]),
            "update_time": datetime.fromtimestamp(cache["update_time"]).isoformat() if cache["update_time"] else None,
            "is_updating": cache["is_updating"],
            "cached_images": total_images,
            "cached_urls": len(downloaded_urls)
        }
    }

@app.get("/api/exports")
async def get_exports():
    """获取所有导出的 JSON 文件列表（按日期分类）"""
    exports = []
    
    if not DATA_EXPORT_DIR.exists():
        return {"code": 0, "data": exports}
    
    # 遍历日期目录
    for date_dir in sorted(DATA_EXPORT_DIR.iterdir(), reverse=True):
        if date_dir.is_dir():
            date = date_dir.name
            files = []
            
            # 获取该日期下的所有 JSON 文件
            for json_file in sorted(date_dir.glob("*.json"), reverse=True):
                stat = json_file.stat()
                files.append({
                    "filename": json_file.name,
                    "time": json_file.stem,  # HHMMSS
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "url": f"/api/exports/{date}/{json_file.name}"
                })
            
            if files:
                exports.append({
                    "date": date,
                    "formatted_date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                    "count": len(files),
                    "files": files
                })
    
    return {"code": 0, "data": exports}

@app.get("/api/exports/{date}/{filename}")
async def get_export_file(date: str, filename: str):
    """获取指定的 JSON 导出文件"""
    file_path = DATA_EXPORT_DIR / date / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 读取并返回 JSON 内容
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)
    
    return {"code": 0, "data": data}

@app.get("/api/exports/latest")
async def get_latest_export():
    """获取最新的导出文件"""
    if not DATA_EXPORT_DIR.exists():
        raise HTTPException(status_code=404, detail="没有导出文件")
    
    # 找到最新的日期目录
    date_dirs = sorted([d for d in DATA_EXPORT_DIR.iterdir() if d.is_dir()], reverse=True)
    if not date_dirs:
        raise HTTPException(status_code=404, detail="没有导出文件")
    
    # 找到最新的文件
    latest_date_dir = date_dirs[0]
    json_files = sorted(latest_date_dir.glob("*.json"), reverse=True)
    
    if not json_files:
        raise HTTPException(status_code=404, detail="没有导出文件")
    
    # 读取最新的文件
    latest_file = json_files[0]
    async with aiofiles.open(latest_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)
    
    return {
        "code": 0,
        "data": data,
        "file_info": {
            "date": latest_date_dir.name,
            "filename": latest_file.name,
            "path": f"/api/exports/{latest_date_dir.name}/{latest_file.name}"
        }
    }

# WebSocket 日志接口
@app.websocket("/api/logs/ws")
async def websocket_logs(websocket: WebSocket):
    """WebSocket 实时日志推送"""
    await log_manager.connect(websocket)
    log_info(f"新的日志客户端连接，当前连接数: {len(log_manager.websockets)}")
    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "clear":
                    log_manager.clear()
                    await websocket.send_json({"type": "cleared"})
                    log_info("日志已被客户端清空")
            except:
                pass
    except WebSocketDisconnect:
        await log_manager.disconnect(websocket)
        log_info(f"日志客户端断开连接，当前连接数: {len(log_manager.websockets)}")

@app.get("/api/logs")
async def get_logs():
    """获取历史日志"""
    return {
        "code": 0,
        "data": log_manager.get_logs()
    }

@app.delete("/api/logs")
async def clear_logs():
    """清空日志"""
    log_manager.clear()
    return {"code": 0, "message": "日志已清空"}

@app.on_event("startup")
async def startup_event():
    """启动时预加载数据"""
    log_info("=" * 50)
    log_info("B站热门视频 API 服务启动")
    log_info(f"服务地址: http://0.0.0.0:8000")
    log_info("=" * 50)

    # 重建已下载URL集合，避免重启后重复下载已有图片
    rebuild_downloaded_urls()

    # 延迟2秒后预加载数据
    await asyncio.sleep(2)
    log_info("开始预加载数据...")
    try:
        cache["is_updating"] = True
        videos = await crawl_hot100()
        cache["data"] = videos
        cache["update_time"] = time.time()
        cache["is_updating"] = False
        log_success(f"预加载完成，共 {len(videos)} 个视频")
    except Exception as e:
        cache["is_updating"] = False
        log_error(f"预加载失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
