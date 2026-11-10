"""Runtime configuration for the Bilibili Hot 100 backend.

Every tunable lives here and can be overridden with an environment variable, so
the rest of the package never reads ``os.environ`` directly.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

__version__ = "2.1.0"

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
DATA_ROOT = Path(os.getenv("BILIBILI_DATA_DIR", str(PROJECT_DIR / "data"))).resolve()
CACHE_DIR = DATA_ROOT / "cache"
IMAGE_CACHE_DIR = CACHE_DIR / "images"
DATA_EXPORT_DIR = DATA_ROOT / "data_exports"
IMAGE_INDEX_FILE = CACHE_DIR / "downloaded_urls.json"
SNAPSHOT_FILE = DATA_ROOT / "snapshot.json"
for _directory in (CACHE_DIR, IMAGE_CACHE_DIR, DATA_EXPORT_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

EXPORT_RETENTION_DAYS = _env_int("BILIBILI_EXPORT_RETENTION_DAYS", 14)
IMAGE_ORPHAN_DAYS = _env_int("BILIBILI_IMAGE_ORPHAN_DAYS", 30)
EXPORT_LIST_LIMIT = _env_int("BILIBILI_EXPORT_LIST_LIMIT", 30)
IMAGE_CACHE_IMMUTABLE_MAX_AGE = 31536000

IMAGE_ROUTE_RE = re.compile(r"^[0-9a-f]{32}\.(?:jpg|jpeg|png|webp|gif)$")
EXPORT_FILE_RE = re.compile(r"^\d{6}\.json$")
DATE_DIR_RE = re.compile(r"^\d{8}$")

# --------------------------------------------------------------------------- #
# HTTP / crawl
# --------------------------------------------------------------------------- #
HOST = os.getenv("BILIBILI_HOST", "127.0.0.1")
PORT = _env_int("BILIBILI_PORT", 8000)
PRELOAD = _env_flag("BILIBILI_PRELOAD", True)
CACHE_TTL_SECONDS = _env_float("BILIBILI_CACHE_TTL", 300.0)

FETCH_PAGE_SIZE = 50
PAGE_COUNT = 2
TARGET_VIDEOS = FETCH_PAGE_SIZE * PAGE_COUNT
MIN_VIDEOS = _env_int("BILIBILI_MIN_VIDEOS", 90)
RETRY_DELAYS: tuple[float, ...] = (0.5, 1.5)
REQUEST_TIMEOUT_SECONDS = 15
IMAGE_TIMEOUT_SECONDS = 10
IMAGE_CONCURRENCY = 10

DEFAULT_ORIGINS = ",".join(
    [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]
)
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
    # Accept-Encoding is intentionally omitted: aiohttp negotiates gzip/deflate
    # (and brotli only when the optional dependency is installed).
}
