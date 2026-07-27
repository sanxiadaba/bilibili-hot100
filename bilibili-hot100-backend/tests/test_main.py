import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request

import main as backend


def make_video(rank: int) -> dict:
    return {
        "aid": rank,
        "bvid": f"BV{rank:010d}",
        "title": f"video {rank}",
        "pic": "https://example.test/cover.jpg",
        "duration": 60,
        "pubdate": 1_700_000_000,
        "owner": {
            "mid": rank,
            "name": f"owner {rank}",
            "face": "https://example.test/avatar.jpg",
        },
        "stat": {
            "view": rank,
            "danmaku": rank,
            "reply": rank,
            "favorite": rank,
            "coin": rank,
            "share": rank,
            "like": rank,
        },
        "tname": "test",
        "rank": rank,
    }


class ValidationTests(unittest.TestCase):
    def test_rejects_partial_snapshot(self):
        with self.assertRaisesRegex(backend.CrawlError, "期望 100"):
            backend.validate_video_batch([make_video(index) for index in range(1, 51)])

    def test_rejects_duplicate_bvid(self):
        videos = [make_video(index) for index in range(1, 101)]
        videos[-1]["bvid"] = videos[0]["bvid"]
        with self.assertRaisesRegex(backend.CrawlError, "重复"):
            backend.validate_video_batch(videos)


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        backend.cache.update(
            data=[],
            update_time=None,
            is_updating=False,
            refresh_id=None,
            last_error=None,
        )

    async def test_failed_refresh_preserves_existing_cache(self):
        existing = [make_video(index) for index in range(1, 101)]
        backend.cache.update(data=existing, update_time=123.0, is_updating=True, refresh_id="test")

        async def fail():
            raise backend.CrawlError("upstream failed")

        with patch.object(backend, "crawl_hot100", fail):
            with self.assertRaises(backend.CrawlError):
                await backend._run_refresh("test")

        self.assertIs(backend.cache["data"], existing)
        self.assertEqual(backend.cache["update_time"], 123.0)
        self.assertFalse(backend.cache["is_updating"])
        self.assertEqual(backend.cache["last_error"], "upstream failed")

    async def test_schedule_refresh_reuses_running_task(self):
        gate = asyncio.Event()

        async def wait_then_succeed():
            await gate.wait()
            return [make_video(index) for index in range(1, 101)]

        with patch.object(backend, "crawl_hot100", wait_then_succeed):
            first, started = backend.schedule_refresh()
            second, started_again = backend.schedule_refresh()
            self.assertTrue(started)
            self.assertFalse(started_again)
            self.assertIs(first, second)
            gate.set()
            await first


class ImageIndexTests(unittest.TestCase):
    def test_missing_index_file_is_not_reported_as_cached(self):
        with tempfile.TemporaryDirectory() as temporary:
            image_root = Path(temporary)
            with patch.object(backend, "IMAGE_CACHE_DIR", image_root):
                backend.image_index.clear()
                backend.image_files_by_name.clear()
                backend.image_index["https://example.test/image.jpg"] = "20260101/missing.jpg"
                self.assertIsNone(backend._resolve_cached_image("https://example.test/image.jpg"))
                self.assertEqual(backend.image_index, {})


class ApiSecurityTests(unittest.TestCase):
    def test_mutation_from_unknown_origin_is_rejected(self):
        request = Request(
            {
                "type": "http",
                "method": "DELETE",
                "path": "/api/logs",
                "headers": [(b"origin", b"https://example.invalid")],
            }
        )
        with self.assertRaises(HTTPException) as raised:
            backend.require_allowed_origin(request)
        self.assertEqual(raised.exception.status_code, 403)

    def test_local_frontend_origin_is_allowed(self):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/refresh",
                "headers": [(b"origin", b"http://127.0.0.1:3000")],
            }
        )
        self.assertIsNone(backend.require_allowed_origin(request))


if __name__ == "__main__":
    unittest.main()
