"""Candidate profile scraper engine: scrape profiles from multiple sources.

Supported sources:
  - google_search: Google Custom Search for public profiles
  - github: GitHub user search API (public)
  - stackoverflow: StackOverflow users search
  - linkedin_public: LinkedIn public profile scrape (limited)
  - custom_url: Fetch and parse a custom profiles page

Each source returns a list of scraped candidate dicts with:
  name, email, headline, location, skills, experience_years, source, source_url,
  profile_url, summary, github_username, linkedin_url, raw_text
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.scrapers.candidates")
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


def _extract_experience(text: str) -> float | None:
    m = re.search(r"(\d{1,2})\s*\+?\s*years?", text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _extract_visa(text: str) -> str | None:
    m = re.search(r"\b(H1B|OPT|GC EAD|GC|L1|TN|F1|Citizen|Green Card)\b", text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _extract_email(text: str) -> str | None:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Source: Google Custom Search
# ---------------------------------------------------------------------------

def scrape_google_profiles(
    query: str,
    location: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    api_key = settings.GOOGLE_API_KEY
    cx = settings.GOOGLE_CX_ID
    if not api_key or not cx:
        logger.warning("Google API key/CX not configured")
        return []

    results = []
    start = 1
    while len(results) < max_results and start <= 100:
        q = f"{query} resume OR profile OR CV" + (f" {location}" if location else "")
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
                full_text = f"{title} {snippet}"
                skills = _extract_skills(full_text)
                name_m = re.search(r"^([A-Z][a-z]+ [A-Z][a-z]+)", title)
                results.append({
                    "name": _clean(name_m.group(1) if name_m else title[:60]),
                    "email": _extract_email(snippet),
                    "headline": _clean(title[:120]),
                    "location": location,
                    "skills": skills,
                    "experience_years": _extract_experience(full_text),
                    "source": "google_search",
                    "source_url": link,
                    "profile_url": link,
                    "summary": _clean(snippet[:1200]),
                    "github_username": None,
                    "linkedin_url": "linkedin.com" in link and link or None,
                    "visa_status": _extract_visa(full_text),
                    "raw_text": full_text,
                })
            start += 10
        except Exception as exc:
            logger.error("Google profile search error: %s", exc)
            break
        _delay()
    return results[:max_results]


# ---------------------------------------------------------------------------
# Source: GitHub User Search
# ---------------------------------------------------------------------------

def scrape_github_profiles(
    query: str,
    location: str | None = None,
    max_results: int = 25,
    language: str | None = None,
) -> list[dict[str, Any]]:
    results = []
    params: dict[str, Any] = {"q": query, "per_page": min(max_results, 30)}
    if location:
        params["q"] += f" location:{location}"
    if language:
        params["q"] += f" language:{language}"

    try:
        resp = httpx.get(
            "https://api.github.com/search/users",
            params=params,
            headers={**_HEADERS, "Accept": "application/vnd.github.v3+json"},
            timeout=15,
        )
        resp.raise_for_status()
        users = resp.json().get("items", [])
    except Exception as exc:
        logger.error("GitHub search error: %s", exc)
        return []

    for user in users[:max_results]:
        username = user.get("login", "")
        profile_url = user.get("html_url", "")
        # Fetch profile details
        try:
            detail = httpx.get(
                f"https://api.github.com/users/{username}",
                headers={**_HEADERS, "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            ).json()
        except Exception:
            detail = {}

        bio = detail.get("bio", "") or ""
        name = detail.get("name", "") or username
        email = detail.get("email")
        gh_loc = detail.get("location") or location
        blog = detail.get("blog", "")
        company = detail.get("company", "")

        # Fetch recent repos for skill inference
        skills_set: set[str] = set()
        try:
            repos_resp = httpx.get(
                f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10",
                headers={**_HEADERS, "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []
            for repo in repos:
                lang = (repo.get("language") or "").lower()
                if lang:
                    skills_set.add(lang)
                desc = (repo.get("description") or "")
                skills_set.update(_extract_skills(desc))
        except Exception:
            pass

        all_text = f"{name} {bio} {company} {blog}"
        results.append({
            "name": _clean(name),
            "email": email,
            "headline": _clean(f"{company} — {bio[:80]}" if company else bio[:120]),
            "location": _clean(gh_loc),
            "skills": sorted(skills_set) or _extract_skills(all_text),
            "experience_years": None,
            "source": "github",
            "source_url": profile_url,
            "profile_url": profile_url,
            "summary": _clean(bio[:1200]) or _clean(all_text[:1200]),
            "github_username": username,
            "linkedin_url": None,
            "visa_status": _extract_visa(all_text),
            "raw_text": all_text,
        })
        _delay()
    return results


# ---------------------------------------------------------------------------
# Source: StackOverflow Users Search
# ---------------------------------------------------------------------------

def scrape_stackoverflow_profiles(
    query: str,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    results = []
    try:
        resp = httpx.get(
            "https://api.stackexchange.com/2.3/users",
            params={
                "order": "desc",
                "sort": "reputation",
                "intitle": query,
                "site": "stackoverflow",
                "pagesize": min(max_results, 30),
            },
            timeout=15,
        )
        resp.raise_for_status()
        users = resp.json().get("items", [])
    except Exception as exc:
        logger.error("StackOverflow search error: %s", exc)
        return []

    for user in users[:max_results]:
        display = user.get("display_name", "")
        link = user.get("link", "")
        location = user.get("location")
        reputation = user.get("reputation", 0)
        top_tags = [t.get("tag_name", "") for t in user.get("top_tags", [])[:5]]

        all_text = f"{display} {' '.join(top_tags)}"
        results.append({
            "name": _clean(display),
            "email": None,
            "headline": _clean(f"SO rep {reputation} — top: {', '.join(top_tags[:3])}" if top_tags else f"SO rep {reputation}"),
            "location": _clean(location) if location else None,
            "skills": top_tags or _extract_skills(all_text),
            "experience_years": None,
            "source": "stackoverflow",
            "source_url": link,
            "profile_url": link,
            "summary": _clean(f"StackOverflow user with {reputation} reputation. Top tags: {', '.join(top_tags)}."),
            "github_username": None,
            "linkedin_url": None,
            "visa_status": None,
            "raw_text": all_text,
        })
    return results


# ---------------------------------------------------------------------------
# Source: LinkedIn public profile scrape (limited)
# ---------------------------------------------------------------------------

def scrape_linkedin_public(
    query: str,
    location: str | None = None,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    """Scrape LinkedIn public profiles via Google site:linkedin.com/in search."""
    api_key = settings.GOOGLE_API_KEY
    cx = settings.GOOGLE_CX_ID
    if not api_key or not cx:
        logger.warning("Google API key/CX not configured for LinkedIn scrape")
        return []

    results = []
    q = f"site:linkedin.com/in {query}" + (f" {location}" if location else "")
    start = 1
    while len(results) < max_results and start <= 50:
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={api_key}&cx={cx}&q={quote_plus(q)}"
            f"&start={start}&num=min(10, {max_results - len(results)})"
        )
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                break
            for item in items:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                full_text = f"{title} {snippet}"

                name_m = re.search(r"^(.+?)\s*[-–|]", title)
                headline_m = re.search(r"[-–|]\s*(.+?)(?:\s*[-–|]|$)", title)
                skills = _extract_skills(full_text)

                results.append({
                    "name": _clean(name_m.group(1) if name_m else title.split("-")[0].strip()),
                    "email": _extract_email(snippet),
                    "headline": _clean(headline_m.group(1) if headline_m else None),
                    "location": location,
                    "skills": skills,
                    "experience_years": _extract_experience(full_text),
                    "source": "linkedin",
                    "source_url": link,
                    "profile_url": link,
                    "summary": _clean(snippet[:1200]),
                    "github_username": None,
                    "linkedin_url": link,
                    "visa_status": _extract_visa(full_text),
                    "raw_text": full_text,
                })
            start += 10
        except Exception as exc:
            logger.error("LinkedIn scrape error: %s", exc)
            break
        _delay()
    return results[:max_results]


# ---------------------------------------------------------------------------
# Source: Custom URL scraper
# ---------------------------------------------------------------------------

def scrape_custom_profiles_url(url: str, max_results: int = 50) -> list[dict[str, Any]]:
    results = []
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text
    except Exception as exc:
        logger.error("Custom URL scrape error (%s): %s", url, exc)
        return []

    # Extract linkedin/github profile links
    linkedin_links = re.findall(r'https?://(?:www\.)?linkedin\.com/in/[\w-]+/?', text)
    github_links = re.findall(r'https?://(?:www\.)?github\.com/[\w-]+/?', text)

    for link in linkedin_links[:max_results]:
        name_part = link.rstrip("/").split("/")[-1]
        name = name_part.replace("-", " ").title()
        results.append({
            "name": _clean(name),
            "email": None,
            "headline": None,
            "location": None,
            "skills": [],
            "experience_years": None,
            "source": "custom_url",
            "source_url": url,
            "profile_url": link,
            "summary": None,
            "github_username": None,
            "linkedin_url": link,
            "visa_status": None,
            "raw_text": name,
        })

    for link in github_links[:max_results - len(results)]:
        username = link.rstrip("/").split("/")[-1]
        results.append({
            "name": _clean(username),
            "email": None,
            "headline": None,
            "location": None,
            "skills": [],
            "experience_years": None,
            "source": "custom_url",
            "source_url": url,
            "profile_url": link,
            "summary": None,
            "github_username": username,
            "linkedin_url": None,
            "visa_status": None,
            "raw_text": username,
        })

    return results[:max_results]


# ---------------------------------------------------------------------------
# Unified candidate scrape dispatcher
# ---------------------------------------------------------------------------

def scrape_candidates(
    source: str,
    query: str = "",
    location: str | None = None,
    url: str | None = None,
    max_results: int = 25,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Unified entry point: dispatch to the correct source scraper."""
    max_results = min(max_results, settings.SCRAPE_MAX_RESULTS)
    if source == "google_search":
        return scrape_google_profiles(query, location, max_results)
    elif source == "github":
        return scrape_github_profiles(query, location, max_results, language)
    elif source == "stackoverflow":
        return scrape_stackoverflow_profiles(query, max_results)
    elif source == "linkedin":
        return scrape_linkedin_public(query, location, max_results)
    elif source == "custom_url" and url:
        return scrape_custom_profiles_url(url, max_results)
    else:
        raise ValueError(f"Unknown or incomplete scrape source: {source}")
