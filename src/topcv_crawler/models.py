from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class JobRecord:
    url: str
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    salary: str | None = None
    job_level: str | None = None
    employment_type: str | None = None
    posted_at: str | None = None
    deadline: str | None = None
    job_description: str | None = None
    requirements: str | None = None
    benefits: str | None = None
    crawl_time: str | None = None
    source: str | None = "topcv.vn"
    raw_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CrawlError:
    url: str
    stage: str
    error: str
    category: str = "request-failed"


@dataclass(slots=True)
class CrawlSummary:
    jobs: list[JobRecord]
    errors: list[CrawlError]
    visited_listing_urls: list[str]
    discovered_job_urls: list[str]
    block_events: list[CrawlError] = field(default_factory=list)
    stopped_early: bool = False
    batches_processed: int = 0
