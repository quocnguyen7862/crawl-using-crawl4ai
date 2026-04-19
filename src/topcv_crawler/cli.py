from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .config import TopCVCrawlConfig
from .crawler import CrawlBootstrapError, crawl_topcv_jobs, deduplicate_jobs, write_output


def _env_str(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_seed_urls() -> list[str] | None:
    raw = os.getenv("TOPCV_SEED_URLS")
    if raw in (None, ""):
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl TopCV job listings with Crawl4AI.")
    parser.add_argument(
        "--seed-url",
        action="append",
        dest="seed_urls",
        default=_env_seed_urls(),
        required=_env_seed_urls() is None,
        help="TopCV listing URL. Pass multiple times to crawl multiple seed listings.",
    )
    parser.add_argument("--output", default=_env_str("TOPCV_OUTPUT", "output/topcv_jobs.jsonl"), help="Output file path.")
    parser.add_argument("--format", choices=("json", "jsonl"), default=_env_str("TOPCV_OUTPUT_FORMAT", "jsonl"), help="Output format.")
    parser.add_argument("--max-listing-pages", type=int, default=_env_int("TOPCV_MAX_LISTING_PAGES", 1), help="Maximum listing pages per seed.")
    parser.add_argument("--max-jobs", type=int, default=_env_int("TOPCV_MAX_JOBS", 50), help="Maximum number of jobs per run.")
    parser.add_argument("--batch-size", type=int, default=_env_int("TOPCV_BATCH_SIZE", 0), help="Process job detail URLs in sequential batches of this size.")
    parser.add_argument("--batch-cooldown", type=float, default=_env_float("TOPCV_BATCH_COOLDOWN", 0.0), help="Cooldown in seconds between batches.")
    parser.add_argument("--max-concurrent", type=int, default=_env_int("TOPCV_MAX_CONCURRENT", 3), help="Concurrent detail requests.")
    parser.add_argument("--delay", type=float, default=_env_float("TOPCV_DELAY", 1.5), help="Delay between requests in seconds.")
    parser.add_argument("--delay-jitter", type=float, default=_env_float("TOPCV_DELAY_JITTER", 0.0), help="Random jitter added to each delay in seconds.")
    parser.add_argument("--backoff-multiplier", type=float, default=_env_float("TOPCV_BACKOFF_MULTIPLIER", 2.0), help="Backoff multiplier after block signals.")
    parser.add_argument("--block-threshold", type=int, default=_env_int("TOPCV_BLOCK_THRESHOLD", 3), help="Stop crawl after this many block signals.")
    parser.add_argument("--timeout-ms", type=int, default=_env_int("TOPCV_TIMEOUT_MS", 45000), help="Page timeout in milliseconds.")
    parser.add_argument("--retry", type=int, default=_env_int("TOPCV_RETRY", 2), help="Retry count per request.")
    parser.add_argument("--wait-for", default=_env_str("TOPCV_WAIT_FOR"), help="Optional Crawl4AI wait condition.")
    parser.add_argument("--browser-type", choices=("chromium", "firefox"), default=_env_str("TOPCV_BROWSER_TYPE", "chromium"), help="Browser engine to use.")
    parser.add_argument("--proxy-server", default=_env_str("TOPCV_PROXY_SERVER"), help="Optional proxy server, e.g. http://host:port.")
    parser.add_argument("--proxy-username", default=_env_str("TOPCV_PROXY_USERNAME"), help="Optional proxy username.")
    parser.add_argument("--proxy-password", default=_env_str("TOPCV_PROXY_PASSWORD"), help="Optional proxy password.")
    parser.add_argument("--show-errors", action="store_true", default=_env_bool("TOPCV_SHOW_ERRORS", False), help="Print crawl errors after completion.")
    return parser


async def _run(args: argparse.Namespace) -> int:
    config = TopCVCrawlConfig(
        seed_urls=args.seed_urls,
        output_path=Path(args.output),
        output_format=args.format,
        max_listing_pages=args.max_listing_pages,
        max_jobs=args.max_jobs,
        batch_size=args.batch_size or None,
        batch_cooldown_seconds=args.batch_cooldown,
        max_concurrent=args.max_concurrent,
        request_delay_seconds=args.delay,
        delay_jitter_seconds=args.delay_jitter,
        backoff_multiplier=args.backoff_multiplier,
        block_threshold=args.block_threshold,
        page_timeout_ms=args.timeout_ms,
        retry_count=args.retry,
        wait_for=args.wait_for,
        browser_type=args.browser_type,
        proxy_server=args.proxy_server,
        proxy_username=args.proxy_username,
        proxy_password=args.proxy_password,
    )
    try:
        summary = await crawl_topcv_jobs(config)
    except CrawlBootstrapError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1

    summary.jobs = deduplicate_jobs(summary.jobs)
    write_output(summary, config.resolved_output_path(), config.output_format)
    print(
        json.dumps(
            {
                "status": "ok",
                "job_count": len(summary.jobs),
                "error_count": len(summary.errors),
                "block_event_count": len(summary.block_events),
                "stopped_early": summary.stopped_early,
                "batches_processed": summary.batches_processed,
                "output": str(config.resolved_output_path()),
            },
            ensure_ascii=False,
        )
    )
    if args.show_errors and summary.errors:
        print(json.dumps([error.__dict__ for error in summary.errors], ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
