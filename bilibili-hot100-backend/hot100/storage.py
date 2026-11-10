"""Snapshot persistence plus dated JSON exports with retention."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles

from . import config, images
from .logs import log_info, log_success, log_warning
from .models import VideoItem
from .paths import safe_child


def _now() -> datetime:
    return datetime.now().astimezone()


def get_export_dir_by_date() -> Path:
    date_dir = config.DATA_EXPORT_DIR / datetime.now().strftime("%Y%m%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir


def _portable_records(videos: list[dict]) -> list[dict]:
    """Strip upstream-only fields and keep the public data contract.

    Image URLs are *not* rewritten to ``/api/images/...`` so an export stays
    usable outside this machine.
    """
    records: list[dict] = []
    for video in videos:
        try:
            records.append(VideoItem.model_validate(video).model_dump())
        except Exception:  # already validated during the crawl; never fail here
            continue
    return records


async def export_data_to_json(videos: list[dict]) -> Path | None:
    if not videos:
        return None
    now = _now()
    file_path = get_export_dir_by_date() / f"{now:%H%M%S}.json"
    records = _portable_records(videos)
    payload = {
        "export_time": now.isoformat(timespec="seconds"),
        "date": f"{now:%Y-%m-%d}",
        "time": f"{now:%H:%M:%S}",
        "total": len(records),
        "videos": records,
    }
    temporary = file_path.with_suffix(".tmp")
    async with aiofiles.open(temporary, "w", encoding="utf-8") as file:
        await file.write(json.dumps(payload, ensure_ascii=False, indent=2))
    await asyncio.to_thread(os.replace, temporary, file_path)
    return file_path


def prune_exports(max_age_days: int | None = None) -> int:
    """Delete export date directories older than the retention window."""
    days = config.EXPORT_RETENTION_DAYS if max_age_days is None else max_age_days
    if days <= 0 or not config.DATA_EXPORT_DIR.exists():
        return 0
    cutoff = (datetime.now() - timedelta(days=days)).date()
    removed = 0
    for date_dir in sorted(config.DATA_EXPORT_DIR.iterdir()):
        if not date_dir.is_dir() or not config.DATE_DIR_RE.fullmatch(date_dir.name):
            continue
        try:
            day = datetime.strptime(date_dir.name, "%Y%m%d").date()
        except ValueError:
            continue
        if day < cutoff:
            shutil.rmtree(date_dir, ignore_errors=True)
            removed += 1
    if removed:
        log_info(f"清理了 {removed} 个过期导出目录（保留 {days} 天）")
    return removed


async def save_snapshot(videos: list[dict], update_time: float, is_partial: bool) -> None:
    """Persist the last good crawl so a restart never starts with no data."""
    payload = {
        "saved_at": _now().isoformat(timespec="seconds"),
        "update_time": update_time,
        "is_partial": is_partial,
        "total": len(videos),
        "videos": videos,
    }
    snapshot_file = config.SNAPSHOT_FILE
    temporary = snapshot_file.with_suffix(".tmp")
    try:
        async with aiofiles.open(temporary, "w", encoding="utf-8") as file:
            await file.write(json.dumps(payload, ensure_ascii=False))
        await asyncio.to_thread(os.replace, temporary, snapshot_file)
    except Exception as exc:
        log_warning(f"快照写入失败，下次启动将重新抓取: {exc}")


def load_snapshot() -> dict[str, Any] | None:
    """Read the snapshot and remap covers to cached images when possible."""
    from .crawler import normalize_videos  # local import avoids a cycle

    snapshot_file = config.SNAPSHOT_FILE
    if not snapshot_file.exists():
        return None
    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log_warning(f"快照读取失败，忽略: {exc}")
        return None
    if not isinstance(payload, dict):
        return None
    raw_videos = payload.get("videos")
    if not isinstance(raw_videos, list) or not raw_videos:
        log_warning("快照内容为空，忽略")
        return None

    try:
        videos = normalize_videos([video for video in raw_videos if isinstance(video, dict)])
    except Exception as exc:
        log_warning(f"快照不可用，忽略: {exc}")
        return None

    for video in videos:
        pic = video.get("pic")
        if isinstance(pic, str):
            video["pic"] = images.resolve_cached_image(pic) or pic
        owner = video.get("owner")
        if isinstance(owner, dict) and isinstance(owner.get("face"), str):
            owner["face"] = images.resolve_cached_image(owner["face"]) or owner["face"]

    update_time = payload.get("update_time")
    if not isinstance(update_time, (int, float)):
        try:
            update_time = snapshot_file.stat().st_mtime
        except OSError:
            update_time = time.time()

    log_success(
        f"已从快照恢复 {len(videos)} 条视频（快照时间 {payload.get('saved_at', 'unknown')}）"
    )
    return {
        "videos": videos,
        "update_time": float(update_time),
        "is_partial": bool(payload.get("is_partial")),
        "saved_at": payload.get("saved_at"),
        "source": "snapshot",
    }


def list_exports(limit: int = config.EXPORT_LIST_LIMIT) -> dict[str, Any]:
    """Describe the newest ``limit`` export date directories."""
    if not config.DATA_EXPORT_DIR.exists():
        return {"dates": [], "total_dates": 0, "truncated": False}
    date_dirs = sorted(
        [
            path
            for path in config.DATA_EXPORT_DIR.iterdir()
            if path.is_dir() and config.DATE_DIR_RE.fullmatch(path.name)
        ],
        key=lambda path: path.name,
        reverse=True,
    )
    selected = date_dirs[: max(0, limit)]
    dates = []
    for date_dir in selected:
        files = []
        for json_file in sorted(date_dir.glob("*.json"), reverse=True):
            try:
                stat = json_file.stat()
            except OSError:
                continue
            files.append(
                {
                    "filename": json_file.name,
                    "time": json_file.stem,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                    .astimezone()
                    .isoformat(timespec="seconds"),
                    "url": f"/api/exports/{date_dir.name}/{json_file.name}",
                }
            )
        if files:
            name = date_dir.name
            dates.append(
                {
                    "date": name,
                    "formatted_date": f"{name[:4]}-{name[4:6]}-{name[6:]}",
                    "count": len(files),
                    "files": files,
                }
            )
    return {
        "dates": dates,
        "total_dates": len(date_dirs),
        "truncated": len(date_dirs) > len(selected),
    }


def latest_export() -> tuple[Path, dict[str, Any]] | None:
    if not config.DATA_EXPORT_DIR.exists():
        return None
    date_dirs = sorted(
        [
            path
            for path in config.DATA_EXPORT_DIR.iterdir()
            if path.is_dir() and config.DATE_DIR_RE.fullmatch(path.name)
        ],
        reverse=True,
    )
    for date_dir in date_dirs:
        json_files = sorted(date_dir.glob("*.json"), reverse=True)
        if not json_files:
            continue
        latest_file = json_files[0]
        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_warning(f"导出文件读取失败: {exc}")
            continue
        return latest_file, data
    return None


def read_export(date: str, filename: str) -> dict[str, Any] | None:
    path = safe_child(config.DATA_EXPORT_DIR, f"{date}/{filename}")
    if not path or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def image_path(date: str, filename: str) -> Path | None:
    path = safe_child(config.IMAGE_CACHE_DIR, f"{date}/{filename}")
    if not path or not path.is_file():
        return None
    return path
