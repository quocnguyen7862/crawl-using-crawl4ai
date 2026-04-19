from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .config import TopCVCrawlConfig
from .models import JobRecord

DETAIL_REPLACEMENTS = {
    "\r": "\n",
    "\xa0": " ",
}


def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value
    for source, target in DETAIL_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = unescape(normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = "\n".join(line.strip() for line in normalized.splitlines()).strip()
    return normalized or None


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.startswith("utm_")]
    normalized = parsed._replace(query=urlencode(query), fragment="")
    return urlunparse(normalized)


def build_listing_page_url(seed_url: str, page_number: int) -> str:
    parsed = urlparse(seed_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if page_number > 1:
        query["page"] = str(page_number)
    else:
        query.pop("page", None)
    return normalize_url(urlunparse(parsed._replace(query=urlencode(query))))


def is_allowed_domain(url: str, config: TopCVCrawlConfig) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in config.allowed_domains


def is_listing_url(url: str, config: TopCVCrawlConfig) -> bool:
    if not is_allowed_domain(url, config):
        return False
    return any(urlparse(url).path.startswith(prefix) for prefix in config.listing_path_prefixes)


def is_job_detail_url(url: str, config: TopCVCrawlConfig) -> bool:
    if not is_allowed_domain(url, config):
        return False
    path = urlparse(url).path
    return any(re.match(pattern, path) for pattern in config.detail_path_patterns)


def coerce_markdown(markdown: Any) -> str:
    if markdown is None:
        return ""
    if isinstance(markdown, str):
        return markdown
    for attr in ("raw_markdown", "fit_markdown", "markdown"):
        value = getattr(markdown, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(markdown)


def extract_links(result: Any) -> list[str]:
    links_obj = getattr(result, "links", None) or {}
    if isinstance(links_obj, dict):
        candidates = []
        for key in ("internal", "external"):
            value = links_obj.get(key, [])
            if isinstance(value, list):
                candidates.extend(value)
    elif isinstance(links_obj, list):
        candidates = links_obj
    else:
        candidates = []

    extracted: list[str] = []
    for item in candidates:
        if isinstance(item, str):
            extracted.append(item)
        elif isinstance(item, dict):
            href = item.get("href") or item.get("url")
            if href:
                extracted.append(href)
    return extracted


def extract_job_links(result: Any, config: TopCVCrawlConfig) -> list[str]:
    base_url = getattr(result, "url", "")
    links = []
    for href in extract_links(result):
        absolute = normalize_url(urljoin(base_url, href))
        if is_job_detail_url(absolute, config):
            links.append(absolute)
    return list(dict.fromkeys(links))


def _extract_json_ld(html: str) -> dict[str, Any]:
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        payload = match.group(1).strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if isinstance(entry, dict) and entry.get("@type") == "JobPosting":
                return entry
    return {}


def _extract_label_value(markdown: str, label: str) -> str | None:
    pattern = re.compile(rf"{re.escape(label)}\s*\n+(.*?)(?:\n{{2,}}|$)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(markdown)
    if not match:
        return None
    return normalize_whitespace(match.group(1))


def _extract_section(markdown: str, heading: str, stop_headings: tuple[str, ...]) -> str | None:
    stop_pattern = "|".join(re.escape(item) for item in stop_headings)
    pattern = re.compile(
        rf"##\s*{re.escape(heading)}\s*(.*?)(?=\n##\s*(?:{stop_pattern})|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if not match:
        return None
    return normalize_whitespace(match.group(1))


def extract_job_record(result: Any, config: TopCVCrawlConfig) -> JobRecord:
    html = getattr(result, "html", "") or ""
    markdown = coerce_markdown(getattr(result, "markdown", ""))
    metadata = getattr(result, "metadata", {}) or {}
    json_ld = _extract_json_ld(html)

    title = (
        json_ld.get("title")
        or _extract_label_value(markdown, "##")
        or metadata.get("title")
    )
    company_name = None
    hiring_organization = json_ld.get("hiringOrganization")
    if isinstance(hiring_organization, dict):
        company_name = hiring_organization.get("name")
    company_name = company_name or _extract_label_value(markdown, "#")

    job = JobRecord(
        url=normalize_url(getattr(result, "url", "")),
        title=normalize_whitespace(title),
        company_name=normalize_whitespace(company_name),
        location=normalize_whitespace(
            _location_from_json_ld(json_ld) or _extract_label_value(markdown, "Địa điểm") or _extract_label_value(markdown, "## Địa điểm làm việc")
        ),
        salary=normalize_whitespace(_salary_from_json_ld(json_ld) or _extract_label_value(markdown, "Mức lương")),
        job_level=normalize_whitespace(_extract_label_value(markdown, "Cấp bậc")),
        employment_type=normalize_whitespace(json_ld.get("employmentType") or _extract_label_value(markdown, "Hình thức làm việc")),
        posted_at=normalize_whitespace(json_ld.get("datePosted") or _extract_label_value(markdown, "Ngày đăng")),
        deadline=normalize_whitespace(json_ld.get("validThrough") or _extract_label_value(markdown, "Hết hạn ứng tuyển")),
        job_description=_extract_section(
            markdown,
            "Mô tả công việc",
            ("Yêu cầu ứng viên", "Quyền lợi được hưởng", "Địa điểm làm việc", "Thời gian làm việc"),
        ),
        requirements=_extract_section(
            markdown,
            "Yêu cầu ứng viên",
            ("Quyền lợi được hưởng", "Địa điểm làm việc", "Thời gian làm việc"),
        )
        or _extract_label_value(markdown, "Yêu cầu:"),
        benefits=_extract_section(
            markdown,
            "Quyền lợi được hưởng",
            ("Địa điểm làm việc", "Thời gian làm việc"),
        )
        or _extract_label_value(markdown, "Quyền lợi:"),
        crawl_time=datetime.now(timezone.utc).isoformat(),
        source="topcv.vn",
        raw_url=getattr(result, "url", None),
        metadata={"metadata": metadata, "json_ld": json_ld},
    )
    return ensure_required_fields(job, config)


def ensure_required_fields(job: JobRecord, config: TopCVCrawlConfig) -> JobRecord:
    data = job.to_dict()
    for field_name in config.required_fields:
        if field_name not in data:
            raise ValueError(f"Missing required field definition: {field_name}")
    normalized = {}
    for key, value in data.items():
        normalized[key] = value if value not in ("", []) else None
    return replace(job, **normalized)


def _location_from_json_ld(data: dict[str, Any]) -> str | None:
    locations = data.get("jobLocation")
    if not locations:
        return None
    if isinstance(locations, dict):
        locations = [locations]
    parsed_locations = []
    for location in locations:
        address = location.get("address") if isinstance(location, dict) else None
        if not isinstance(address, dict):
            continue
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
        ]
        text = ", ".join(part for part in parts if part)
        if text:
            parsed_locations.append(text)
    return " | ".join(parsed_locations) or None


def _salary_from_json_ld(data: dict[str, Any]) -> str | None:
    salary = data.get("baseSalary")
    if not isinstance(salary, dict):
        return None
    value = salary.get("value")
    currency = salary.get("currency")
    if isinstance(value, dict):
        min_value = value.get("minValue")
        max_value = value.get("maxValue")
        unit = value.get("unitText")
        if min_value or max_value:
            amount = f"{min_value or ''}-{max_value or ''}".strip("-")
            return " ".join(part for part in (amount, currency, unit) if part)
    return None
