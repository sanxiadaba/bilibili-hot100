"""运行时配置。

只保留真正需要调整的开关（数据目录、启动预抓取），其余参数直接写死。
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("BILIBILI_DATA_DIR", str(ROOT / "data"))).resolve()
SNAPSHOT_FILE = DATA_DIR / "snapshot.json"
IMAGE_DIR = DATA_DIR / "images"
WEB_DIST = ROOT / "web" / "dist"

HOST = "127.0.0.1"
PRELOAD = os.getenv("BILIBILI_PRELOAD", "1").strip().lower() not in {"0", "false", "no", "off"}

# 数据超过这个年龄就顺手在后台刷新一次，页面本身不等它。
CACHE_TTL_SECONDS = 300.0
MIN_VIDEOS = 90

PAGE_SIZE = 50
PAGE_COUNT = 2
TARGET_VIDEOS = PAGE_SIZE * PAGE_COUNT
REQUEST_TIMEOUT = 15
IMAGE_TIMEOUT = 10
IMAGE_CONCURRENCY = 8
RETRY_DELAYS = (0.5, 1.5)

BILIBILI_API = "https://api.bilibili.com/x/web-interface/popular"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
IMAGE_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://www.bilibili.com",
    "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
}

# 列表封面 160x90、头像 24px，取这个尺寸足够清晰，体积只有原图的几十分之一。
COVER_SIZE = (480, 270)
AVATAR_SIZE = (96, 96)


def ensure_dirs() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
