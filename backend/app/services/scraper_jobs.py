"""Job scraper engine: scrape job postings from multiple sources.

Supported sources:
  - google_jobs: Google Custom Search API for job listings
  - rss_feed: Parse RSS/Atom feeds from job boards
  - indeed_search: Indeed scrape (HTML parsing)
  - naukri_search: Naukri scrape (HTML parsing)
  - custom_url: Fetch and parse a custom careers page

Each source returns a list of scraped job dicts with:
  title, company, location, url, description, skills, source, source_url,
  salary_min, salary_max, currency, posted_at, is_remote, raw_text
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.scrapers.jobs")
settings = get_settings()

_HEADERS = {"User-Agent": settings.SCRAPE_USER_AGENT}


def _delay():
    time.sleep(settings.SCRAPE_DELAY_SECONDS)


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()


def _extract_skills(text: str) -> list[str]:
    from app.services.contract_parser import SKILLS_LEXICON

    if not text:
        return []
    low = text.lower()
    return sorted({s for s in SKILLS_LEXICON if re.search(r"\b" + re.escape(s) + r"\b", low)})


def _parse_salary(text: str) -> tuple[float | None, float | None, str | None]:
    if not text:
        return None, None, None
    currency = "USD"
    if "$" in text:
        currency = "USD"
    elif "₹" in text or "inr" in text.lower():
        currency = "INR"
    elif "€" in text or "eur" in text.lower():
        currency = "EUR"
    elif "£" in text or "gbp" in text.lower():
        currency = "GBP"
    nums = re.findall(r"[\d,]+(?:\.\d+)?", text.replace(",", ""))
    vals = []
    for n in nums:
        try:
            v = float(n)
            if v > 1000000:
                v = v / 12  # annual to monthly
            vals.append(v)
        except ValueError:
            pass
    if len(vals) >= 2:
        return vals[0], vals[1], currency
    if len(vals) == 1:
        return vals[0], None, currency
    return None, None, None


# ---------------------------------------------------------------------------
# Source: Google Custom Search
# ---------------------------------------------------------------------------

def scrape_google_jobs(
    query: str,
    location: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    api_key = settings.GOOGLE_API_KEY
    cx = settings.GOOGLE_CX_ID
    if not api_key or not cx:
        logger.warning("Google API key or CX ID not configured, using fallback")
        return []

    results = []
    start = 1
    while len(results) < max_results and start <= 100:
        q = f"{query} job" + (f" in {location}" if location else "")
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={api_key}&cx={cx}&q={quote_plus(q)}"
            f"&start={start}&num=min(10, {max_results - len(results)})"
        )
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                link = item.get("link", "")
                skills = _extract_skills(snippet + " " + title)
                sal_min, sal_max, currency = _parse_salary(snippet)
                results.append({
                    "title": _clean(title),
                    "company": None,
                    "location": location,
                    "url": link,
                    "description": _clean(snippet),
                    "skills": skills,
                    "source": "google_jobs",
                    "source_url": link,
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "currency": currency,
                    "posted_at": None,
                    "is_remote": "remote" in (snippet + title).lower(),
                    "raw_text": snippet,
                })
            start += 10
        except Exception as exc:
            logger.error("Google search error: %s", exc)
            break
        _delay()
    return results[:max_results]


# ---------------------------------------------------------------------------
# Source: RSS/Atom Feed
# ---------------------------------------------------------------------------

def scrape_rss_feed(feed_url: str, max_results: int = 50) -> list[dict[str, Any]]:
    results = []
    try:
        resp = httpx.get(feed_url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        logger.error("RSS feed error (%s): %s", feed_url, exc)
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    for item in items[:max_results]:
        title = (item.findtext("title") or item.findtext("atom:title", namespaces=ns) or "").strip()
        link = (item.findtext("link") or "")
        if not link:
            link_el = item.find("atom:link", ns)
            if link_el is not None:
                link = link_el.get("href", "")
        desc = (item.findtext("description") or item.findtext("atom:summary", namespaces=ns) or "").strip()
        desc_clean = re.sub(r"<[^>]+>", "", desc)
        pub = item.findtext("pubDate") or item.findtext("atom:published", namespaces=ns)

        skills = _extract_skills(title + " " + desc_clean)
        sal_min, sal_max, currency = _parse_salary(desc_clean)

        results.append({
            "title": _clean(title),
            "company": None,
            "location": None,
            "url": link.strip(),
            "description": _clean(desc_clean[:2000]),
            "skills": skills,
            "source": "rss_feed",
            "source_url": feed_url,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "currency": currency,
            "posted_at": pub,
            "is_remote": "remote" in (title + desc_clean).lower(),
            "raw_text": desc_clean,
        })
    return results


# ---------------------------------------------------------------------------
# Source: Indeed (HTML scrape)
# ---------------------------------------------------------------------------

def scrape_indeed(
    query: str,
    location: str | None = None,
    max_results: int = 25,
    country: str = "us",
) -> list[dict[str, Any]]:
    base = f"https://{country}.indeed.com"
    results = []
    for start in range(0, max_results, 10):
        params = {"q": query, "start": start}
        if location:
            params["l"] = location
        try:
            resp = httpx.get(
                f"{base}/jobs",
                params=params,
                headers=_HEADERS,
                timeout=15,
                follow_redirects=True,
            )
            if resp.status_code == 403:
                logger.warning("Indeed blocked request (403)")
                break
            text = resp.text
            # Extract job cards from HTML
            cards = re.findall(
                r'<div[^>]*class="[^"]*job_seen_beacon[^"]*"[^>]*>(.*?)</div>\s*</div>',
                text, re.DOTALL,
            )
            if not cards:
                # Fallback: extract from data attributes
                cards = re.findall(r'data-jk="([^"]+)"', text)

            for card in cards[: max_results - len(results)]:
                if isinstance(card, str) and len(card) < 10:
                    continue
                title_m = re.search(r'<h2[^>]*>(.*?)</h2>', card if isinstance(card, str) else "", re.DOTALL)
                title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else None
                link_m = re.search(r'href="(/rc/clk[^"]+)"', card if isinstance(card, str) else "")
                url = (base + link_m.group(1)) if link_m else None
                company_m = re.search(r'<span[^>]*data-testid="company-name"[^>]*>(.*?)</span>', card if isinstance(card, str) else "")
                company = re.sub(r"<[^>]+>", "", company_m.group(1)).strip() if company_m else None
                loc_m = re.search(r'<div[^>]*data-testid="text-location"[^>]*>(.*?)</div>', card if isinstance(card, str) else "")
                loc = re.sub(r"<[^>]+>", "", loc_m.group(1)).strip() if loc_m else location

                desc_text = re.sub(r"<[^>]+>", "", card if isinstance(card, str) else "")
                skills = _extract_skills(desc_text + " " + (title or ""))
                sal_min, sal_max, currency = _parse_salary(desc_text)

                results.append({
                    "title": _clean(title),
                    "company": _clean(company),
                    "location": _clean(loc),
                    "url": url,
                    "description": _clean(desc_text[:2000]),
                    "skills": skills,
                    "source": "indeed",
                    "source_url": f"{base}/jobs?q={quote_plus(query)}",
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "currency": currency,
                    "posted_at": None,
                    "is_remote": "remote" in desc_text.lower(),
                    "raw_text": desc_text,
                })
            if len(results) >= max_results:
                break
        except Exception as exc:
            logger.error("Indeed scrape error: %s", exc)
            break
        _delay()
    return results[:max_results]


# ---------------------------------------------------------------------------
# Source: Naukri (HTML scrape)
# ---------------------------------------------------------------------------

def scrape_naukri(
    query: str,
    location: str | None = None,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    results = []
    pages = (max_results + 9) // 10
    for page in range(1, pages + 1):
        params = {"q": query, "pageNo": page}
        if location:
            params["l"] = location
        try:
            resp = httpx.get(
                "https://www.naukri.com/jobs",
                params=params,
                headers={**_HEADERS, "Accept-Language": "en-US,en;q=0.9"},
                timeout=15,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                break
            text = resp.text
            cards = re.findall(r'<article[^>]*class="[^"]*tuple[^"]*"[^>]*>(.*?)</article>', text, re.DOTALL)

            for card in cards[: max_results - len(results)]:
                title_m = re.search(r'<a[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>', card, re.DOTALL)
                title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else None
                href_m = re.search(r'href="([^"]+)"', card)
                url = href_m.group(1) if href_m else None
                if url and not url.startswith("http"):
                    url = "https://www.naukri.com" + url
                company_m = re.search(r'<a[^>]*class="[^"]*companyName[^"]*"[^>]*>(.*?)</a>', card, re.DOTALL)
                company = re.sub(r"<[^>]+>", "", company_m.group(1)).strip() if company_m else None
                loc_m = re.search(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</span>', card, re.DOTALL)
                loc = re.sub(r"<[^>]+>", "", loc_m.group(1)).strip() if loc_m else location

                desc_text = re.sub(r"<[^>]+>", "", card)
                skills = _extract_skills(desc_text + " " + (title or ""))
                sal_min, sal_max, currency = _parse_salary(desc_text)

                results.append({
                    "title": _clean(title),
                    "company": _clean(company),
                    "location": _clean(loc),
                    "url": url,
                    "description": _clean(desc_text[:2000]),
                    "skills": skills,
                    "source": "naukri",
                    "source_url": f"https://www.naukri.com/jobs?q={quote_plus(query)}",
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "currency": currency or "INR",
                    "posted_at": None,
                    "is_remote": "remote" in desc_text.lower(),
                    "raw_text": desc_text,
                })
            if len(results) >= max_results:
                break
        except Exception as exc:
            logger.error("Naukri scrape error: %s", exc)
            break
        _delay()
    return results[:max_results]


# ---------------------------------------------------------------------------
# Source: Custom URL (careers page scraper)
# ---------------------------------------------------------------------------

def scrape_custom_url(url: str, max_results: int = 50) -> list[dict[str, Any]]:
    results = []
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text
    except Exception as exc:
        logger.error("Custom URL scrape error (%s): %s", url, exc)
        return []

    # Extract links that look like job postings
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, re.DOTALL)
    job_keywords = re.compile(
        r"(job|position|role|career|opening|requisition|vacancy|apply|hiring)",
        re.IGNORECASE,
    )

    for href, link_text in links:
        clean_text = re.sub(r"<[^>]+>", "", link_text).strip()
        if not clean_text or len(clean_text) < 5:
            continue
        if not job_keywords.search(clean_text):
            continue
        full_url = urljoin(url, href)
        skills = _extract_skills(clean_text)

        results.append({
            "title": _clean(clean_text),
            "company": None,
            "location": None,
            "url": full_url,
            "description": _clean(clean_text),
            "skills": skills,
            "source": "custom_url",
            "source_url": url,
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "posted_at": None,
            "is_remote": False,
            "raw_text": clean_text,
        })
        if len(results) >= max_results:
            break
    return results


# ---------------------------------------------------------------------------
# Unified scrape dispatcher
# ---------------------------------------------------------------------------

def scrape_jobs(
    source: str,
    query: str = "",
    location: str | None = None,
    url: str | None = None,
    feed_url: str | None = None,
    max_results: int = 25,
    country: str = "us",
) -> list[dict[str, Any]]:
    """Unified entry point: dispatch to the correct source scraper."""
    max_results = min(max_results, settings.SCRAPE_MAX_RESULTS)
    if source == "google_jobs":
        return scrape_google_jobs(query, location, max_results)
    elif source == "indeed":
        return scrape_indeed(query, location, max_results, country)
    elif source == "naukri":
        return scrape_naukri(query, location, max_results)
    elif source == "rss_feed" and feed_url:
        return scrape_rss_feed(feed_url, max_results)
    elif source == "custom_url" and url:
        return scrape_custom_url(url, max_results)
    else:
        raise ValueError(f"Unknown or incomplete scrape source: {source}")
