from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.topcv_crawler.config import TopCVCrawlConfig
from src.topcv_crawler.crawler import CrawlBootstrapError, crawl_topcv_jobs, deduplicate_jobs, write_output
from src.topcv_crawler.parser import build_listing_page_url, extract_job_links, extract_job_record, is_job_detail_url


class FakeCrawler:
    def __init__(self, pages):
        self.pages = pages

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch(self, url: str):
        page = self.pages.get(url)
        if isinstance(page, Exception):
            raise page
        if page is None:
            raise RuntimeError(f"missing fixture for {url}")
        return page


def make_result(url: str, *, links=None, html="", markdown="", success=True):
    return SimpleNamespace(
        url=url,
        links=links or {},
        html=html,
        markdown=markdown,
        metadata={},
        success=success,
        error_message=None if success else "request failed",
        status_code=200 if success else 429,
    )


DETAIL_MARKDOWN = """# Công ty Cổ phần TOPCV Việt Nam

## Chuyên Viên Triển Khai Phần Mềm

Mức lương

Thoả thuận

Địa điểm

Hà Nội, Thanh Xuân

Hết hạn ứng tuyển

2026-12-31

Hình thức làm việc

Toàn thời gian

## Mô tả công việc

Triển khai phần mềm cho khách hàng doanh nghiệp.

## Yêu cầu ứng viên

Tối thiểu 2 năm kinh nghiệm.

## Quyền lợi được hưởng

Bảo hiểm xã hội, Thưởng tháng 13
"""


DETAIL_HTML = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Chuyên Viên Triển Khai Phần Mềm",
  "datePosted": "2026-04-18",
  "validThrough": "2026-12-31",
  "employmentType": "FULL_TIME",
  "hiringOrganization": {"name": "Công ty Cổ phần TOPCV Việt Nam"},
  "jobLocation": {
    "@type": "Place",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "47 Nguyễn Tuân",
      "addressLocality": "Thanh Xuân",
      "addressRegion": "Hà Nội"
    }
  }
}
</script>
</head>
<body></body>
</html>
"""


class TopCVCrawlerTests(unittest.TestCase):
    def setUp(self):
        self.workspace_tmp = Path("test_output")
        self.workspace_tmp.mkdir(exist_ok=True)

    def tearDown(self):
        for path in sorted(self.workspace_tmp.glob("**/*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if self.workspace_tmp.exists():
            self.workspace_tmp.rmdir()

    def test_build_listing_page_url(self):
        self.assertEqual(
            build_listing_page_url("https://www.topcv.vn/viec-lam?keyword=python", 2),
            "https://www.topcv.vn/viec-lam?keyword=python&page=2",
        )

    def test_is_job_detail_url(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"])
        self.assertTrue(is_job_detail_url("https://www.topcv.vn/viec-lam/devops-engineer/123456.html", config))
        self.assertTrue(
            is_job_detail_url(
                "https://www.topcv.vn/brand/topcv/tuyen-dung/chuyen-vien-trien-khai-phan-mem-j1837316.html",
                config,
            )
        )
        self.assertFalse(is_job_detail_url("https://www.topcv.vn/blog/foo", config))

    def test_extract_job_links_filters_candidates(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"])
        result = make_result(
            "https://www.topcv.vn/viec-lam",
            links={
                "internal": [
                    {"href": "/viec-lam/devops-engineer/123456.html"},
                    {"href": "/brand/topcv/tuyen-dung/chuyen-vien-trien-khai-phan-mem-j1837316.html"},
                    {"href": "/blog/kinh-nghiem"},
                ]
            },
        )
        links = extract_job_links(result, config)
        self.assertEqual(
            links,
            [
                "https://www.topcv.vn/viec-lam/devops-engineer/123456.html",
                "https://www.topcv.vn/brand/topcv/tuyen-dung/chuyen-vien-trien-khai-phan-mem-j1837316.html",
            ],
        )

    def test_extract_job_record_prefers_json_ld_and_markdown_sections(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"])
        result = make_result(
            "https://www.topcv.vn/brand/topcv/tuyen-dung/chuyen-vien-trien-khai-phan-mem-j1837316.html",
            html=DETAIL_HTML,
            markdown=DETAIL_MARKDOWN,
        )
        job = extract_job_record(result, config)
        self.assertEqual(job.title, "Chuyên Viên Triển Khai Phần Mềm")
        self.assertEqual(job.company_name, "Công ty Cổ phần TOPCV Việt Nam")
        self.assertEqual(job.employment_type, "FULL_TIME")
        self.assertIn("Triển khai phần mềm", job.job_description or "")
        self.assertIn("2 năm kinh nghiệm", job.requirements or "")

    def test_crawl_continues_when_one_detail_fails(self):
        listing_url = "https://www.topcv.vn/viec-lam"
        ok_url = "https://www.topcv.vn/viec-lam/devops-engineer/123456.html"
        bad_url = "https://www.topcv.vn/viec-lam/data-engineer/999999.html"
        config = TopCVCrawlConfig(
            seed_urls=[listing_url],
            max_listing_pages=1,
            max_jobs=10,
            request_delay_seconds=0,
        )
        fake_crawler = FakeCrawler(
            {
                listing_url: make_result(
                    listing_url,
                    links={"internal": [{"href": ok_url}, {"href": bad_url}, {"href": ok_url}]},
                ),
                ok_url: make_result(ok_url, html=DETAIL_HTML, markdown=DETAIL_MARKDOWN),
                bad_url: RuntimeError("detail timeout"),
            }
        )
        summary = asyncio.run(crawl_topcv_jobs(config, crawler=fake_crawler))
        self.assertEqual(len(summary.jobs), 1)
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].stage, "detail")

    def test_bootstrap_failure_raises(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"], request_delay_seconds=0)
        fake_crawler = FakeCrawler({"https://www.topcv.vn/viec-lam": RuntimeError("seed failed")})
        with self.assertRaises(CrawlBootstrapError):
            asyncio.run(crawl_topcv_jobs(config, crawler=fake_crawler))

    def test_write_output_jsonl(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"])
        result = make_result(
            "https://www.topcv.vn/viec-lam/devops-engineer/123456.html",
            html=DETAIL_HTML,
            markdown=DETAIL_MARKDOWN,
        )
        job = extract_job_record(result, config)
        output = self.workspace_tmp / "jobs.jsonl"
        summary = SimpleNamespace(jobs=deduplicate_jobs([job]), errors=[])
        write_output(summary, output, "jsonl")
        lines = output.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["title"], "Chuyên Viên Triển Khai Phần Mềm")

    def test_block_response_is_classified_and_stops_early(self):
        listing_url = "https://www.topcv.vn/viec-lam"
        first_bad = "https://www.topcv.vn/viec-lam/blocked/111111.html"
        second_bad = "https://www.topcv.vn/viec-lam/blocked/222222.html"
        config = TopCVCrawlConfig(
            seed_urls=[listing_url],
            request_delay_seconds=0,
            delay_jitter_seconds=0,
            block_threshold=1,
        )
        fake_crawler = FakeCrawler(
            {
                listing_url: make_result(
                    listing_url,
                    links={"internal": [{"href": first_bad}, {"href": second_bad}]},
                ),
                first_bad: RuntimeError("HTTP 429: Too many requests"),
                second_bad: RuntimeError("HTTP 429: Too many requests"),
            }
        )
        summary = asyncio.run(crawl_topcv_jobs(config, crawler=fake_crawler))
        self.assertTrue(summary.stopped_early)
        self.assertEqual(len(summary.block_events), 1)
        self.assertEqual(summary.block_events[0].category, "block-suspected")

    def test_write_output_json_includes_block_metadata(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"])
        result = make_result(
            "https://www.topcv.vn/viec-lam/devops-engineer/123456.html",
            html=DETAIL_HTML,
            markdown=DETAIL_MARKDOWN,
        )
        job = extract_job_record(result, config)
        output = self.workspace_tmp / "jobs.json"
        summary = SimpleNamespace(
            jobs=deduplicate_jobs([job]),
            errors=[],
            block_events=[SimpleNamespace(url="u", stage="detail", error="HTTP 429", category="block-suspected")],
            stopped_early=False,
            batches_processed=1,
        )
        write_output(summary, output, "json")
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["block_event_count"], 1)
        self.assertFalse(payload["stopped_early"])
        self.assertEqual(len(payload["jobs"]), 1)

    def test_jitter_delay_is_used(self):
        config = TopCVCrawlConfig(seed_urls=["https://www.topcv.vn/viec-lam"], request_delay_seconds=1.0, delay_jitter_seconds=0.5)
        with patch("src.topcv_crawler.crawler.random.uniform", return_value=0.25), patch(
            "src.topcv_crawler.crawler.asyncio.sleep",
            new=AsyncMock(),
        ) as mocked_sleep:
            asyncio.run(__import__("src.topcv_crawler.crawler", fromlist=["_sleep_with_jitter"])._sleep_with_jitter(config, 1.0))
        mocked_sleep.assert_awaited_once_with(1.25)

    def test_processes_detail_urls_in_batches(self):
        listing_url = "https://www.topcv.vn/viec-lam"
        urls = [
            "https://www.topcv.vn/viec-lam/job-one/111111.html",
            "https://www.topcv.vn/viec-lam/job-two/222222.html",
            "https://www.topcv.vn/viec-lam/job-three/333333.html",
        ]
        config = TopCVCrawlConfig(
            seed_urls=[listing_url],
            max_jobs=3,
            batch_size=2,
            batch_cooldown_seconds=0,
            request_delay_seconds=0,
            delay_jitter_seconds=0,
        )
        fake_crawler = FakeCrawler(
            {
                listing_url: make_result(listing_url, links={"internal": [{"href": url} for url in urls]}),
                urls[0]: make_result(urls[0], html=DETAIL_HTML, markdown=DETAIL_MARKDOWN),
                urls[1]: make_result(urls[1], html=DETAIL_HTML, markdown=DETAIL_MARKDOWN),
                urls[2]: make_result(urls[2], html=DETAIL_HTML, markdown=DETAIL_MARKDOWN),
            }
        )
        summary = asyncio.run(crawl_topcv_jobs(config, crawler=fake_crawler))
        self.assertEqual(len(summary.jobs), 3)
        self.assertEqual(summary.batches_processed, 2)


if __name__ == "__main__":
    unittest.main()
