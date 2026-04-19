from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class TopCVCrawlConfig:
    seed_urls: list[str]
    output_path: Path = Path("output/topcv_jobs.jsonl")
    output_format: Literal["json", "jsonl"] = "jsonl"
    max_listing_pages: int = 1
    max_jobs: int = 50
    batch_size: int | None = None
    batch_cooldown_seconds: float = 0.0
    max_concurrent: int = 3
    request_delay_seconds: float = 1.5
    delay_jitter_seconds: float = 0.0
    backoff_multiplier: float = 2.0
    block_threshold: int = 3
    page_timeout_ms: int = 45000
    retry_count: int = 2
    wait_for: str | None = None
    headless: bool = True
    browser_type: Literal["chromium", "firefox"] = "chromium"
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    allowed_domains: tuple[str, ...] = ("www.topcv.vn", "topcv.vn")
    listing_path_prefixes: tuple[str, ...] = ("/viec-lam",)
    detail_path_patterns: tuple[str, ...] = (
        r"^/viec-lam/[^?#]+/\d+\.html$",
        r"^/brand/[^?#]+/tuyen-dung/[^?#]+-j\d+\.html$",
    )
    required_fields: tuple[str, ...] = (
        "url",
        "title",
        "company_name",
        "location",
        "salary",
        "job_level",
        "employment_type",
        "posted_at",
        "deadline",
        "job_description",
        "requirements",
        "benefits",
        "crawl_time",
        "source",
    )
    output_dir: Path | None = field(default=None, repr=False)

    def resolved_output_path(self) -> Path:
        if self.output_dir is not None:
            return self.output_dir / self.output_path.name
        return self.output_path

    def effective_batch_size(self) -> int:
        if self.batch_size is None or self.batch_size <= 0:
            return self.max_jobs
        return min(self.batch_size, self.max_jobs)

    @property
    def proxy_config(self) -> dict[str, str] | None:
        if not self.proxy_server:
            return None
        config = {"server": self.proxy_server}
        if self.proxy_username:
            config["username"] = self.proxy_username
        if self.proxy_password:
            config["password"] = self.proxy_password
        return config
