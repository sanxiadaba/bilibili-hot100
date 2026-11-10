"""Generate a deterministic offline snapshot used by the E2E workflow.

Usage::

    python tests/make_fixture.py [output_path]

The default output is ``tests/fixtures/snapshot.json``. CI copies it to
``data/snapshot.json`` and starts the backend with ``BILIBILI_PRELOAD=0`` so the
browser tests never touch the real Bilibili API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CATEGORIES = ["动画", "游戏", "科技", "生活", "知识"]


def make_video(rank: int) -> dict:
    category = CATEGORIES[(rank - 1) % len(CATEGORIES)]
    return {
        "aid": rank,
        "bvid": f"BV1fixture{rank:04d}",
        "title": f"离线测试视频 {rank:03d}",
        "pic": f"https://example.test/cover-{rank:03d}.jpg",
        "duration": 60 + rank,
        "pubdate": 1_700_000_000 + rank * 60,
        "owner": {
            "mid": rank,
            "name": f"UP主 {rank:03d}",
            "face": f"https://example.test/face-{rank:03d}.jpg",
        },
        "stat": {
            "view": rank * 1000,
            "danmaku": rank,
            "reply": rank * 2,
            "favorite": rank * 3,
            "coin": rank * 4,
            "share": rank * 5,
            "like": rank * 100,
        },
        "tname": category,
        "rank": rank,
    }


def build_payload() -> dict:
    videos = [make_video(rank) for rank in range(1, 101)]
    return {
        "saved_at": "2026-01-01T00:00:00+08:00",
        "update_time": 1767225600.0,
        "is_partial": False,
        "total": len(videos),
        "videos": videos,
    }


def main() -> int:
    default = Path(__file__).resolve().parent / "fixtures" / "snapshot.json"
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {payload['total']} videos to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
