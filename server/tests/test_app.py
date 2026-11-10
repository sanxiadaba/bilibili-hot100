from __future__ import annotations

import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from server import app as api
from server import config, crawler, images, store
from server.crawler import CrawlError
from server.logs import log_manager


def make_video(rank: int) -> dict:
    return {
        "aid": rank,
        "bvid": f"BV{rank:010d}",
        "title": f"video {rank}",
        "pic": "https://example.test/cover.jpg",
        "duration": 60,
        "pubdate": 1_700_000_000,
        "owner": {"mid": rank, "name": f"owner {rank}", "face": "https://example.test/face.jpg"},
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


def make_videos(count: int = 100) -> list[dict]:
    return [make_video(index) for index in range(1, count + 1)]


def make_request(origin: str | None) -> Request:
    headers = [(b"host", b"127.0.0.1:8000")]
    if origin:
        headers.append((b"origin", origin.encode()))
    return Request({"type": "http", "method": "POST", "path": "/api/refresh", "headers": headers})


class NormalizeTests(unittest.TestCase):
    def test_rejects_result_that_lost_a_page(self):
        with self.assertRaisesRegex(CrawlError, "至少 90"):
            crawler.normalize_videos(make_videos(50))

    def test_duplicates_are_dropped_and_reranked(self):
        videos = make_videos(100)
        videos[-1]["bvid"] = videos[0]["bvid"]
        normalized = crawler.normalize_videos(videos)
        self.assertEqual(len(normalized), 99)
        self.assertEqual([video["rank"] for video in normalized], list(range(1, 100)))

    def test_invalid_item_does_not_fail_the_batch(self):
        videos = make_videos(100)
        videos[7]["title"] = None
        normalized = crawler.normalize_videos(videos)
        self.assertEqual(len(normalized), 99)
        self.assertNotIn(8, [video["aid"] for video in normalized])

    def test_unknown_upstream_fields_are_removed(self):
        videos = make_videos(100)
        videos[0]["upstream_only"] = "x"
        normalized = crawler.normalize_videos(videos)
        self.assertNotIn("upstream_only", normalized[0])

    def test_partial_result_above_threshold_is_accepted(self):
        self.assertEqual(len(crawler.normalize_videos(make_videos(95))), 95)


class FetchRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_failure_is_retried(self):
        attempts = []

        async def flaky(_session, page, _page_size):
            attempts.append(page)
            if len(attempts) < 3:
                raise CrawlError("网络异常")
            return [make_video(1)]

        with (
            patch.object(crawler, "_fetch_once", flaky),
            patch.object(config, "RETRY_DELAYS", (0, 0)),
        ):
            videos = await crawler.fetch_page(None, 1)

        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(videos), 1)

    async def test_persistent_failure_gives_up(self):
        attempts = []

        async def broken(_session, page, _page_size):
            attempts.append(page)
            raise ValueError("not json")

        with (
            patch.object(crawler, "_fetch_once", broken),
            patch.object(config, "RETRY_DELAYS", (0, 0)),
            self.assertRaisesRegex(CrawlError, "第 1 页"),
        ):
            await crawler.fetch_page(None, 1)

        self.assertEqual(len(attempts), len(config.RETRY_DELAYS) + 1)


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        store.reset()

    async def test_failed_refresh_keeps_existing_cache(self):
        existing = make_videos()
        store.cache.update(videos=existing, update_time=123.0)

        async def fail():
            raise CrawlError("upstream down")

        with (
            patch.object(store.crawler, "crawl", fail),
            patch.object(store, "save_snapshot", AsyncMock()),
            self.assertRaises(CrawlError),
        ):
            await store.refresh()

        self.assertIs(store.cache["videos"], existing)
        self.assertEqual(store.cache["update_time"], 123.0)
        self.assertFalse(store.cache["is_updating"])
        self.assertEqual(store.cache["last_error"], "upstream down")

    async def test_schedule_reuses_the_running_task(self):
        gate = asyncio.Event()

        async def wait_then_succeed():
            await gate.wait()
            return make_videos(), False, 1_700_000_000.0

        with (
            patch.object(store.crawler, "crawl", wait_then_succeed),
            patch.object(store, "save_snapshot", AsyncMock()),
            patch.object(store.images, "prune", lambda _urls: 0),
        ):
            self.assertTrue(store.schedule())
            self.assertFalse(store.schedule())
            gate.set()
            await asyncio.sleep(0.05)

        self.assertFalse(store.cache["is_updating"])
        self.assertEqual(store.cache["source"], "live")
        self.assertEqual(len(store.cache["videos"]), 100)


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        store.reset()

    async def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(config, "DATA_DIR", root),
                patch.object(config, "SNAPSHOT_FILE", root / "snapshot.json"),
            ):
                await store.save_snapshot(make_videos(), 789.0, True)
                payload = store.load_snapshot()

        self.assertIsNotNone(payload)
        videos, update_time, is_partial = payload
        self.assertEqual(len(videos), 100)
        self.assertEqual(update_time, 789.0)
        self.assertTrue(is_partial)
        self.assertEqual(videos[0]["pic"], "https://example.test/cover.jpg")

    async def test_corrupt_snapshot_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot.json"
            snapshot.write_text("{oops", encoding="utf-8")
            with patch.object(config, "SNAPSHOT_FILE", snapshot):
                self.assertIsNone(store.load_snapshot())


class ImageTests(unittest.TestCase):
    def setUp(self):
        images.files.clear()

    def test_thumbnail_suffix(self):
        self.assertEqual(
            images.thumb("http://i0.hdslb.com/a.jpg", (480, 270)),
            "https://i0.hdslb.com/a.jpg@480w_270h_1c.webp",
        )

    def test_existing_suffix_is_kept(self):
        url = "https://i0.hdslb.com/a.jpg@100w.webp"
        self.assertEqual(images.thumb(url, (96, 96)), url)

    def test_sniff_rejects_html(self):
        self.assertIsNone(images._sniff(b"<!doctype html><html>"))
        self.assertEqual(images._sniff(b"\xff\xd8\xff\xe0rest"), "jpg")
        self.assertEqual(images._sniff(b"RIFF____WEBPrest"), "webp")

    def test_decorate_uses_local_file_and_keeps_source(self):
        cover = images.thumb("https://example.test/cover.jpg", (480, 270))
        face = images.thumb("https://example.test/face.jpg", (96, 96))
        images.files[images.key(cover)] = "a" * 32 + ".webp"
        images.files[images.key(face)] = "b" * 32 + ".webp"
        source = make_videos(1)

        decorated = images.decorate(source)

        self.assertTrue(decorated[0]["pic"].startswith("/img/"))
        self.assertTrue(decorated[0]["owner"]["face"].startswith("/img/"))
        self.assertEqual(source[0]["pic"], "https://example.test/cover.jpg")


class ApiSecurityTests(unittest.TestCase):
    def test_cross_site_refresh_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            api.require_same_origin(make_request("https://evil.example"))
        self.assertEqual(raised.exception.status_code, 403)

    def test_local_origin_and_curl_are_allowed(self):
        self.assertIsNone(api.require_same_origin(make_request("http://127.0.0.1:8000")))
        # Vite 开发服务器（:3000）通过代理访问时 Host 会变成 :8000，来源仍应放行。
        self.assertIsNone(api.require_same_origin(make_request("http://127.0.0.1:3000")))
        self.assertIsNone(api.require_same_origin(make_request(None)))


class ApiTests(unittest.TestCase):
    def setUp(self):
        store.reset()
        images.files.clear()
        log_manager.clear()
        self.client = TestClient(api.app, base_url="http://127.0.0.1:8000")

    def tearDown(self):
        store.reset()
        images.files.clear()
        log_manager.clear()

    def test_status_reports_empty_state(self):
        body = self.client.get("/api/status").json()
        self.assertEqual(body["total"], 0)
        self.assertTrue(body["stale"])
        self.assertIn("data_dir", body)

    def test_hot100_is_503_before_the_first_crawl(self):
        response = self.client.get("/api/hot100")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_hot100_serves_cache(self):
        store.cache.update(videos=make_videos(), update_time=time.time(), is_partial=True)
        response = self.client.get("/api/hot100")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 100)
        self.assertTrue(body["is_partial"])
        self.assertFalse(body["is_stale"])
        # 没有本地缓存时，图片退到 B站缩略图，而不是原图。
        self.assertIn("@480w_270h_1c.webp", body["data"][0]["pic"])

    def test_refresh_rejects_cross_site_origin(self):
        response = self.client.post("/api/refresh", headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status_code, 403)

    def test_refresh_starts_a_task(self):
        with patch.object(store, "schedule", return_value=True):
            response = self.client.post("/api/refresh", headers={"Origin": "http://127.0.0.1:8000"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"started": True})

    def test_export_keeps_origin_urls(self):
        store.cache.update(videos=make_videos(), update_time=time.time())
        response = self.client.get("/api/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertEqual(response.json()["videos"][0]["pic"], "https://example.test/cover.jpg")

    def test_export_404_without_data(self):
        self.assertEqual(self.client.get("/api/export").status_code, 404)

    def test_image_route_rejects_traversal_and_bad_names(self):
        self.assertEqual(self.client.get("/img/..%2F..%2Frun.py").status_code, 404)
        self.assertEqual(self.client.get("/img/" + "a" * 32 + ".exe").status_code, 404)

    def test_logs_can_be_cleared(self):
        from server.logs import log_info

        log_info("hello")
        self.assertEqual(len(self.client.get("/api/logs").json()["data"]), 1)
        response = self.client.delete("/api/logs", headers={"Origin": "http://127.0.0.1:8000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/logs").json()["data"], [])


if __name__ == "__main__":
    unittest.main()
