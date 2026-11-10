"""生成一份离线快照，供 E2E 使用，不访问 B站。"""

from __future__ import annotations

import json
import sys
import time
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
    now = time.time()
    return {
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        # 用当前时间，避免快照被判为过期而触发真实抓取，E2E 才能完全离线。
        "update_time": now,
        "is_partial": False,
        "total": len(videos),
        "videos": videos,
    }


def main() -> int:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("snapshot.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {payload['total']} videos to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
