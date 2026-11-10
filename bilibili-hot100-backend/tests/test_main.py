import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from hot100 import api, config, crawler, images, state, storage
from hot100.crawler import CrawlError


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


def make_videos(count: int = 100) -> list:
    return [make_video(index) for index in range(1, count + 1)]


class NormalizeTests(unittest.TestCase):
    def test_rejects_snapshot_that_lost_a_page(self):
        with self.assertRaisesRegex(CrawlError, "至少 90"):
            crawler.normalize_videos(make_videos(50))

    def test_duplicate_bvid_is_deduped_and_reranked(self):
        videos = make_videos(100)
        videos[-1]["bvid"] = videos[0]["bvid"]
        normalized = crawler.normalize_videos(videos)
        self.assertEqual(len(normalized), 99)
        self.assertEqual([video["rank"] for video in normalized], list(range(1, 100)))

    def test_invalid_item_is_skipped_instead_of_failing_the_batch(self):
        videos = make_videos(100)
        videos[7]["title"] = None
        normalized = crawler.normalize_videos(videos)
        self.assertEqual(len(normalized), 99)
        self.assertNotIn(8, [video["aid"] for video in normalized])

    def test_partial_result_above_threshold_is_accepted(self):
        normalized = crawler.normalize_videos(make_videos(95))
        self.assertEqual(len(normalized), 95)


class FetchRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_failure_is_retried(self):
        attempts = []

        async def flaky(_session, page, _page_size):
            attempts.append(page)
            if len(attempts) < 3:
                raise CrawlError("网络异常: boom")
            return [make_video(1)]

        with (
            patch.object(crawler, "_fetch_page_once", flaky),
            patch.object(config, "RETRY_DELAYS", (0, 0)),
        ):
            videos = await crawler.fetch_page(None, 1)

        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(videos), 1)

    async def test_persistent_failure_gives_up_after_retries(self):
        attempts = []

        async def broken(_session, page, _page_size):
            attempts.append(page)
            raise CrawlError("请求超时")

        with (
            patch.object(crawler, "_fetch_page_once", broken),
            patch.object(config, "RETRY_DELAYS", (0, 0)),
            self.assertRaisesRegex(CrawlError, "第 1 页"),
        ):
            await crawler.fetch_page(None, 1)

        self.assertEqual(len(attempts), len(config.RETRY_DELAYS) + 1)


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        state.reset_cache()

    async def test_failed_refresh_preserves_existing_cache(self):
        existing = make_videos()
        state.cache.update(data=existing, update_time=123.0, is_updating=True, refresh_id="test")

        async def fail():
            raise CrawlError("upstream failed")

        with patch.object(state, "crawl_hot100", fail), self.assertRaises(CrawlError):
            await state._run_refresh("test")

        self.assertIs(state.cache["data"], existing)
        self.assertEqual(state.cache["update_time"], 123.0)
        self.assertFalse(state.cache["is_updating"])
        self.assertEqual(state.cache["last_error"], "upstream failed")

    async def test_schedule_refresh_reuses_running_task(self):
        gate = asyncio.Event()

        async def wait_then_succeed():
            await gate.wait()
            return make_videos(), False, 1_700_000_000.0

        with patch.object(state, "crawl_hot100", wait_then_succeed):
            first, started = state.schedule_refresh()
            second, started_again = state.schedule_refresh()
            self.assertTrue(started)
            self.assertFalse(started_again)
            self.assertIs(first, second)
            gate.set()
            await first

        self.assertFalse(state.cache["is_updating"])
        self.assertEqual(state.cache["source"], "live")
        self.assertEqual(state.cache["is_partial"], False)


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        images.image_index.clear()
        images.image_files_by_name.clear()
        state.reset_cache()

    async def test_snapshot_round_trip_restores_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot.json"
            image_root = root / "images"
            image_root.mkdir()
            (root / "exports").mkdir()
            with (
                patch.object(config, "SNAPSHOT_FILE", snapshot),
                patch.object(config, "IMAGE_CACHE_DIR", image_root),
                patch.object(config, "DATA_EXPORT_DIR", root / "exports"),
            ):
                await storage.save_snapshot(make_videos(), 789.0, True)
                self.assertTrue(snapshot.exists())
                payload = storage.load_snapshot()

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(len(payload["videos"]), 100)
        self.assertEqual(payload["update_time"], 789.0)
        self.assertTrue(payload["is_partial"])
        self.assertEqual(payload["source"], "snapshot")
        # No cached file on disk: covers must stay on the origin URL.
        self.assertEqual(payload["videos"][0]["pic"], "https://example.test/cover.jpg")

    async def test_corrupt_snapshot_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "snapshot.json"
            snapshot.write_text("{not json", encoding="utf-8")
            with patch.object(config, "SNAPSHOT_FILE", snapshot):
                self.assertIsNone(storage.load_snapshot())


class ExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_export_contains_only_contract_fields_and_origin_urls(self):
        videos = make_videos(3)
        videos[0]["upstream_only_field"] = "internal"
        videos[0]["pic"] = "https://example.test/origin.jpg"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(config, "DATA_EXPORT_DIR", root):
                path = await storage.export_data_to_json(videos)
                assert path is not None
                imported = json.loads(path.read_text(encoding="utf-8"))

        record = imported["videos"][0]
        self.assertEqual(imported["total"], 3)
        self.assertEqual(record["rank"], 1)
        self.assertEqual(record["pic"], "https://example.test/origin.jpg")
        self.assertNotIn("upstream_only_field", record)

    def test_prune_exports_removes_only_old_dates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / "20200101"
            fresh = root / (time.strftime("%Y%m%d"))
            old.mkdir()
            fresh.mkdir()
            (old / "000000.json").write_text("{}", encoding="utf-8")
            (fresh / "000000.json").write_text("{}", encoding="utf-8")
            with patch.object(config, "DATA_EXPORT_DIR", root):
                removed = storage.prune_exports(max_age_days=7)
            self.assertEqual(removed, 1)
            self.assertFalse(old.exists())
            self.assertTrue(fresh.exists())


class ImageIndexTests(unittest.TestCase):
    def test_missing_index_file_is_not_reported_as_cached(self):
        with tempfile.TemporaryDirectory() as temporary:
            image_root = Path(temporary)
            with patch.object(config, "IMAGE_CACHE_DIR", image_root):
                images.image_index.clear()
                images.image_files_by_name.clear()
                images.image_index["https://example.test/image.jpg"] = "20260101/missing.jpg"
                self.assertIsNone(images.resolve_cached_image("https://example.test/image.jpg"))
                self.assertEqual(images.image_index, {})


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
            api.require_allowed_origin(request)
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
        self.assertIsNone(api.require_allowed_origin(request))


class ApiTests(unittest.TestCase):
    """Endpoint-level tests; no lifespan, no crawler, no network."""

    def setUp(self):
        self.client = TestClient(api.app)
        state.reset_cache()

    def tearDown(self):
        state.reset_cache()

    def test_status_reports_empty_state(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["total_videos"], 0)
        self.assertIn("is_partial", body)
        self.assertIn("data_dir", body)

    def test_hot100_returns_503_without_data(self):
        async def fail():
            raise CrawlError("upstream down")

        with patch.object(state, "crawl_hot100", fail):
            response = self.client.get("/api/hot100")
        self.assertEqual(response.status_code, 503)

    def test_hot100_serves_cached_data(self):
        state.cache.update(
            data=make_videos(), update_time=time.time(), is_partial=True, source="live"
        )
        response = self.client.get("/api/hot100")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 100)
        self.assertTrue(body["from_cache"])
        self.assertTrue(body["is_partial"])
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_force_refresh_is_rejected(self):
        state.cache.update(data=make_videos(), update_time=time.time())
        response = self.client.get("/api/hot100?force_refresh=true")
        self.assertEqual(response.status_code, 400)

    def test_refresh_rejects_unknown_origin(self):
        response = self.client.post("/api/refresh", headers={"Origin": "https://example.invalid"})
        self.assertEqual(response.status_code, 403)

    def test_image_route_rejects_traversal(self):
        response = self.client.get("/api/images/..%2F..%2Fmain.py/x.jpg")
        self.assertEqual(response.status_code, 404)

    def test_exports_listing_is_paginated_and_empty_safe(self):
        response = self.client.get("/api/exports?limit=5")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body["data"], list)
        self.assertIn("truncated", body)


if __name__ == "__main__":
    unittest.main()
