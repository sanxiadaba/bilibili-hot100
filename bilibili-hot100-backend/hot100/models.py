"""Pydantic models that define the public data contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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
    rcmd_reason: dict[str, Any] | None = None


class Hot100Response(BaseModel):
    code: int
    message: str
    data: list[VideoItem]
    update_time: str
    from_cache: bool
    is_partial: bool = False
    source: str = "live"
