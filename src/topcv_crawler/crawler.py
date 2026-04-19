from __future__ import annotations

import asyncio
import json
import random
import re
from pathlib import Path
from typing import Any

from .config import TopCVCrawlConfig
from .models import CrawlError, CrawlSummary, JobRecord
from .parser import (
    build_listing_page_url,
    coerce_markdown,
    extract_job_links,
    extract_job_record,
    normalize_url,
)


class CrawlBootstrapError(RuntimeError):
    """Raised when no configured seed URL can be accessed."""


class Crawl4AIAdapter:
    def __init__(self, config: TopCVCrawlConfig):
        self.config = config
        self._crawler = None

    async def __aenter__(self) -> "Crawl4AIAdapter":
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        except ImportError as exc:
            raise RuntimeError(
                "crawl4ai is not installed. Install requirements with Python 3.11+ before running the crawler."
            ) from exc

        self._run_config_cls = CrawlerRunConfig
        browser_config = BrowserConfig(
            browser_type=self.config.browser_type,
            headless=self.config.headless,
            user_agent=self.config.user_agent,
            viewport_width=1440,
            viewport_height=2400,
            proxy_config=self.config.proxy_config,
        )
        self._crawler = AsyncWebCrawler(config=browser_config)
        await self._crawler.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._crawler is not None:
            await self._crawler.__aexit__(exc_type, exc, tb)

    async def fetch(self, url: str) -> Any:
        run_config = self._run_config_cls(
            page_timeout=self.config.page_timeout_ms,
            wait_for=self.config.wait_for,
            remove_overlay_elements=True,
        )
        return await self._crawler.arun(url=url, config=run_config)


async def crawl_topcv_jobs(
    config: TopCVCrawlConfig,
    crawler: Crawl4AIAdapter | Any | None = None,
) -> CrawlSummary:
    owned_crawler = crawler is None
    visited_listing_urls: list[str] = []
    discovered_job_urls: list[str] = []
    errors: list[CrawlError] = []
    block_events: list[CrawlError] = []
    jobs: list[JobRecord] = []
    seen_job_urls: set[str] = set()
    bootstrap_success = False
    stopped_early = False
    batches_processed = 0

    if owned_crawler:
        crawler = Crawl4AIAdapter(config)

    async with crawler:
        for seed_url in config.seed_urls:
            for page_number in range(1, config.max_listing_pages + 1):
                if _should_stop_early(block_events, config):
                    stopped_early = True
                    break
                page_url = build_listing_page_url(seed_url, page_number)
                try:
                    listing_result = await _fetch_with_retry(crawler, page_url, config.retry_count)
                except Exception as exc:  # noqa: BLE001
                    crawl_error = _build_crawl_error(page_url, "listing", exc)
                    errors.append(crawl_error)
                    if crawl_error.category == "block-suspected":
                        block_events.append(crawl_error)
                    await _sleep_with_jitter(config, _backoff_delay(config, len(block_events), crawl_error.category))
                    continue

                bootstrap_success = True
                visited_listing_urls.append(page_url)
                for detail_url in extract_job_links(listing_result, config):
                    if detail_url not in seen_job_urls:
                        seen_job_urls.add(detail_url)
                        discovered_job_urls.append(detail_url)
                    if len(discovered_job_urls) >= config.max_jobs:
                        break

                if len(discovered_job_urls) >= config.max_jobs:
                    break
                await _sleep_with_jitter(config, config.request_delay_seconds)
            if stopped_early:
                break

        if not bootstrap_success:
            raise CrawlBootstrapError("Unable to access any configured TopCV seed URL.")

        semaphore = asyncio.Semaphore(config.max_concurrent)
        target_urls = discovered_job_urls[: config.max_jobs]
        batch_size = config.effective_batch_size()

        async def process_job(detail_url: str) -> None:
            nonlocal stopped_early
            if _should_stop_early(block_events, config):
                stopped_early = True
                return
            async with semaphore:
                try:
                    detail_result = await _fetch_with_retry(crawler, detail_url, config.retry_count)
                    jobs.append(extract_job_record(detail_result, config))
                except Exception as exc:  # noqa: BLE001
                    crawl_error = _build_crawl_error(detail_url, "detail", exc)
                    errors.append(crawl_error)
                    if crawl_error.category == "block-suspected":
                        block_events.append(crawl_error)
                finally:
                    category = block_events[-1].category if block_events else "request-failed"
                    await _sleep_with_jitter(config, _backoff_delay(config, len(block_events), category))

        for batch_start in range(0, len(target_urls), batch_size):
            if _should_stop_early(block_events, config):
                stopped_early = True
                break
            batch_urls = target_urls[batch_start : batch_start + batch_size]
            if not batch_urls:
                break
            await asyncio.gather(*(process_job(url) for url in batch_urls))
            batches_processed += 1
            if batch_start + batch_size < len(target_urls):
                await _sleep_with_jitter(config, config.batch_cooldown_seconds)

    return CrawlSummary(
        jobs=jobs,
        errors=errors,
        visited_listing_urls=visited_listing_urls,
        discovered_job_urls=discovered_job_urls,
        block_events=block_events,
        stopped_early=stopped_early or _should_stop_early(block_events, config),
        batches_processed=batches_processed,
    )


async def _fetch_with_retry(crawler: Any, url: str, retry_count: int) -> Any:
    last_error: Exception | None = None
    for _ in range(retry_count + 1):
        try:
            result = await crawler.fetch(url)
            success = getattr(result, "success", True)
            if success is False:
                error_message = getattr(result, "error_message", "crawl failed")
                status_code = getattr(result, "status_code", None)
                if status_code is not None:
                    error_message = f"HTTP {status_code}: {error_message}"
                raise RuntimeError(error_message)
            if _result_looks_blocked(result):
                status_code = getattr(result, "status_code", None)
                status_prefix = f"HTTP {status_code}: " if status_code is not None else ""
                raise RuntimeError(f"{status_prefix}block challenge detected")
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    assert last_error is not None
    raise last_error


def write_output(summary: CrawlSummary, output_path: Path, output_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [job.to_dict() for job in summary.jobs]
    if output_format == "json":
        output_path.write_text(
            json.dumps(
                {
                    "jobs": payload,
                    "block_event_count": len(summary.block_events),
                    "stopped_early": summary.stopped_early,
                    "batches_processed": summary.batches_processed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    with output_path.open("w", encoding="utf-8") as handle:
        for record in payload:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def deduplicate_jobs(jobs: list[JobRecord]) -> list[JobRecord]:
    unique: dict[str, JobRecord] = {}
    for job in jobs:
        unique[normalize_url(job.url)] = job
    return list(unique.values())


def _build_crawl_error(url: str, stage: str, exc: Exception) -> CrawlError:
    error_text = str(exc)
    category = "block-suspected" if _looks_like_block(error_text) else "request-failed"
    return CrawlError(url=url, stage=stage, error=error_text, category=category)


def _looks_like_block(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "403",
            "429",
            "rate limit",
            "rate-limit",
            "blocked",
            "forbidden",
            "challenge",
            "captcha",
            "too many requests",
            "access denied",
        )
    )


def _result_looks_blocked(result: Any) -> bool:
    status_code = getattr(result, "status_code", None)
    if status_code in {403, 429}:
        return True
    html = getattr(result, "html", "") or ""
    markdown = coerce_markdown(getattr(result, "markdown", ""))
    combined = " ".join(part for part in (html, markdown) if isinstance(part, str)).lower()
    return any(
        re.search(pattern, combined) is not None
        for pattern in (
            r"\btoo many requests\b",
            r"\bverify (you are|that you are) human\b",
            r"\bcaptcha\b",
            r"\brate limit(?:ed)?\b",
            r"\btemporarily blocked\b",
        )
    )


def _should_stop_early(block_events: list[CrawlError], config: TopCVCrawlConfig) -> bool:
    return config.block_threshold > 0 and len(block_events) >= config.block_threshold


def _backoff_delay(config: TopCVCrawlConfig, block_count: int, category: str) -> float:
    if category != "block-suspected" or block_count <= 0:
        return config.request_delay_seconds
    return config.request_delay_seconds * (config.backoff_multiplier ** block_count)


async def _sleep_with_jitter(config: TopCVCrawlConfig, base_delay: float) -> None:
    effective_delay = max(0.0, base_delay)
    if config.delay_jitter_seconds > 0:
        effective_delay += random.uniform(0, config.delay_jitter_seconds)
    if effective_delay > 0:
        await asyncio.sleep(effective_delay)
