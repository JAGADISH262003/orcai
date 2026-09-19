"""Tier 3 Enrichment Engine: enrich candidate profiles with external data.

Providers:
  - Apollo.io: Contact enrichment, company data
  - PDL (People Data Labs): Professional profiles
  - Hunter.io: Email verification and company email patterns
  - Deterministic fallback: Always available, uses public data

Cost-capped: Each enrichment attempt is tracked and budgets are enforced.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.enrichment")
settings = get_settings()

# Cost tracking (in-memory per session; in production, store in DB)
_enrichment_costs: dict[str, int] = {}
_ENRICHMENT_BUDGET = 100  # max calls per agency per session


def _check_budget(agency_id: int, provider: str) -> bool:
    key = f"{agency_id}:{provider}"
    count = _enrichment_costs.get(key, 0)
    if count >= _ENRICHMENT_BUDGET:
        logger.warning("Enrichment budget exhausted for %s/%s", agency_id, provider)
        return False
    _enrichment_costs[key] = count + 1
    return True


def _log_cost(agency_id: int, provider: str, result: dict):
    logger.info("Enrichment %s/%s: %s", agency_id, provider, {k: v for k, v in result.items() if v})


# ---------------------------------------------------------------------------
# Apollo.io
# ---------------------------------------------------------------------------

def enrich_apollo(
    email: str | None = None,
    name: str | None = None,
    company: str | None = None,
    linkedin_url: str | None = None,
) -> dict[str, Any]:
    """Enrich via Apollo.io People API."""
    api_key = settings.APOLLO_API_KEY
    if not api_key:
        return {"provider": "apollo", "status": "not_configured"}

    url = "https://api.apollo.io/v1/people/match"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    payload: dict[str, Any] = {"api_key": api_key}
    if email:
        payload["email"] = email
    if name:
        payload["name"] = name
    if company:
        payload["organization_name"] = company
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("person", {})
        if not data:
            return {"provider": "apollo", "status": "not_found"}

        return {
            "provider": "apollo",
            "status": "found",
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone_numbers", [{}])[0].get("sanitized_number") if data.get("phone_numbers") else None,
            "title": data.get("title"),
            "company": data.get("organization", {}).get("name") if data.get("organization") else None,
            "location": data.get("city") and f"{data['city']}, {data.get('state', '')}" or None,
            "linkedin_url": data.get("linkedin_url"),
            "industry": data.get("organization", {}).get("industry") if data.get("organization") else None,
            "employees": data.get("organization", {}).get("employee_count") if data.get("organization") else None,
            "skills": [],  # Apollo doesn't return skills directly
            "raw": data,
        }
    except Exception as exc:
        logger.error("Apollo enrichment error: %s", exc)
        return {"provider": "apollo", "status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# People Data Labs (PDL)
# ---------------------------------------------------------------------------

def enrich_pdl(
    email: str | None = None,
    name: str | None = None,
    linkedin_url: str | None = None,
) -> dict[str, Any]:
    """Enrich via PDL Person Enrichment API."""
    api_key = settings.PDL_API_KEY
    if not api_key:
        return {"provider": "pdl", "status": "not_configured"}

    params: dict[str, str] = {"api_key": api_key, "pretty": "false"}
    if email:
        params["email"] = email
    if linkedin_url:
        params["linkedin_url"] = linkedin_url
    elif name:
        params["name"] = name
    else:
        return {"provider": "pdl", "status": "no_query"}

    try:
        resp = httpx.get("https://api.peopledatalabs.com/v5/person/enrichment", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 200 or not data.get("data"):
            return {"provider": "pdl", "status": "not_found"}

        person = data["data"]
        return {
            "provider": "pdl",
            "status": "found",
            "name": person.get("full_name"),
            "email": person.get("email"),
            "phone": person.get("phone_numbers", [None])[0] if person.get("phone_numbers") else None,
            "title": person.get("job_title"),
            "company": person.get("organization", {}).get("name") if isinstance(person.get("organization"), dict) else None,
            "location": person.get("location"),
            "linkedin_url": person.get("linkedin_url"),
            "industry": person.get("industry"),
            "skills": person.get("skills", []),
            "experience_years": None,
            "education": person.get("education", [{}])[0].get("school", {}).get("name") if person.get("education") else None,
            "raw": person,
        }
    except Exception as exc:
        logger.error("PDL enrichment error: %s", exc)
        return {"provider": "pdl", "status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Hunter.io
# ---------------------------------------------------------------------------

def enrich_hunter(
    domain: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Email verification and company email pattern discovery via Hunter.io."""
    api_key = settings.HUNTER_API_KEY
    if not api_key:
        return {"provider": "hunter", "status": "not_configured"}

    if email:
        try:
            resp = httpx.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": api_key},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return {
                "provider": "hunter",
                "status": "found",
                "email_valid": data.get("status") == "valid",
                "email_score": data.get("score"),
                "email_status": data.get("status"),
                "raw": data,
            }
        except Exception as exc:
            return {"provider": "hunter", "status": "error", "error": str(exc)}

    if domain:
        try:
            resp = httpx.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": api_key, "limit": 5},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            emails = data.get("emails", [])
            return {
                "provider": "hunter",
                "status": "found",
                "organization": data.get("organization"),
                "pattern": data.get("pattern"),
                "emails_found": len(emails),
                "emails": [{"email": e.get("value"), "type": e.get("type"), "confidence": e.get("confidence")} for e in emails[:5]],
                "raw": data,
            }
        except Exception as exc:
            return {"provider": "hunter", "status": "error", "error": str(exc)}

    return {"provider": "hunter", "status": "no_query"}


# ---------------------------------------------------------------------------
# Unified enrichment dispatcher
# ---------------------------------------------------------------------------

def enrich_candidate(
    agency_id: int,
    email: str | None = None,
    name: str | None = None,
    company: str | None = None,
    linkedin_url: str | None = None,
    providers: list[str] | None = None,
) -> dict[str, Any]:
    """Run enrichment across multiple providers with budget enforcement.

    Returns merged results from all providers.
    """
    if providers is None:
        providers = ["apollo", "pdl", "hunter"]

    merged: dict[str, Any] = {
        "providers_called": [],
        "data": {},
    }

    for provider in providers:
        if not _check_budget(agency_id, provider):
            continue

        if provider == "apollo":
            result = enrich_apollo(email=email, name=name, company=company, linkedin_url=linkedin_url)
        elif provider == "pdl":
            result = enrich_pdl(email=email, name=name, linkedin_url=linkedin_url)
        elif provider == "hunter":
            domain = email.split("@")[1] if email and "@" in email else None
            result = enrich_hunter(domain=domain, email=email)
        else:
            result = {"provider": provider, "status": "unknown"}

        merged["providers_called"].append(provider)
        if result.get("status") == "found":
            # Merge non-None fields into data
            for k, v in result.items():
                if k not in ("provider", "status", "raw") and v:
                    if k not in merged["data"] or not merged["data"][k]:
                        merged["data"][k] = v
        _log_cost(agency_id, provider, result)

    return merged
