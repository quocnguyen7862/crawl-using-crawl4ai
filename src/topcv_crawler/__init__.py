"""TopCV crawler package built around Crawl4AI."""

from .config import TopCVCrawlConfig
from .crawler import crawl_topcv_jobs
from .models import CrawlError, CrawlSummary, JobRecord

__all__ = [
    "TopCVCrawlConfig",
    "crawl_topcv_jobs",
    "CrawlError",
    "CrawlSummary",
    "JobRecord",
]
