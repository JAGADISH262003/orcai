"""AI-powered batch resume screening, skills extraction, and market intelligence."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.seeker import Seeker
from app.services.llm import chat_json
from app.services.skills_taxonomy import (
    find_skills_in_text,
    normalize_skills,
    skill_gap,
)

logger = logging.getLogger("orcai.ai_screening")


def _extract_text_from_resume(seeker: Seeker) -> str:
    """Build a text blob from a seeker's profile for skill extraction."""
    parts = []
    if seeker.name:
        parts.append(f"Name: {seeker.name}")
    if seeker.headline:
        parts.append(f"Headline: {seeker.headline}")
    if seeker.summary:
        parts.append(f"Summary: {seeker.summary}")
    if seeker.skills:
        parts.append(f"Skills: {', '.join(seeker.skills)}")
    if seeker.resume_text:
        parts.append(seeker.resume_text[:4000])
    return "\n".join(parts)


def score_resume_against_contract(
    seeker: Seeker,
    contract: Contract,
) -> dict[str, Any]:
    """Deterministic scoring of a seeker against a contract."""
    required = contract.skills or []
    candidate_skills = seeker.skills or []

    matched = set(normalize_skills(required)) & set(normalize_skills(candidate_skills))
    missing = set(normalize_skills(required)) - set(normalize_skills(candidate_skills))
    extra = set(normalize_skills(candidate_skills)) - set(normalize_skills(required))

    total_required = len(required) if required else 1
    coverage = len(matched) / total_required * 100

    exp_years = seeker.experience_years or 0
    exp_min = contract.experience_min or 0
    exp_met = exp_years >= exp_min if exp_min else True

    # Composite score
    skill_score = coverage
    exp_score = min(100, (exp_years / exp_min * 100)) if exp_min else 80
    overall = skill_score * 0.7 + exp_score * 0.3

    tier = "A" if overall >= 80 else "B" if overall >= 60 else "C"

    return {
        "overall_score": round(overall, 1),
        "skill_coverage": round(coverage, 1),
        "skill_score": round(skill_score, 1),
        "experience_score": round(exp_score, 1),
        "experience_met": exp_met,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "extra_skills": sorted(extra),
        "tier": tier,
    }


def batch_screen(
    db: Session,
    agency_id: int,
    contract_id: int,
    seeker_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Batch screen multiple seekers against a single contract."""
    contract = db.get(Contract, contract_id)
    if contract is None or contract.agency_id != agency_id:
        return [{"error": "Contract not found"}]

    q = db.query(Seeker).filter(Seeker.agency_id == agency_id, Seeker.is_active)
    if seeker_ids:
        q = q.filter(Seeker.id.in_(seeker_ids))
    seekers = q.all()

    results = []
    for seeker in seekers:
        score_data = score_resume_against_contract(seeker, contract)
        results.append({
            "seeker_id": seeker.id,
            "seeker_name": seeker.name,
            "seeker_headline": seeker.headline,
            "seeker_skills": seeker.skills or [],
            **score_data,
        })

    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return results


async def extract_skills_from_text(text: str) -> list[str]:
    """Use AI to extract skills from arbitrary text (resume, JD, etc.)."""
    # Deterministic first
    found = find_skills_in_text(text)

    # Try AI enhancement
    system = (
        "You are a skill extraction assistant. Extract all professional skills, "
        "tools, technologies, and certifications from the text. Return a JSON object: "
        '{"skills": ["skill1", "skill2", ...]}. '
        "Return lowercase skill names. Include versions where relevant (e.g. 'python 3.11'). "
        "Return at most 30 skills."
    )
    result = await chat_json(system, f"Text to extract skills from:\n\n{text[:6000]}")
    if result and "skills" in result:
        ai_skills = normalize_skills(result["skills"])
        combined = list(dict.fromkeys(found + ai_skills))
        return combined[:30]

    return found[:30]


async def get_market_intelligence(
    job_title: str,
    skills: list[str],
    location: str | None = None,
) -> dict[str, Any]:
    """Get market intelligence data for a role (salary, demand, competition)."""
    system = (
        "You are a recruiting market intelligence analyst. "
        "For the given role and skills, return a JSON object with:\n"
        '"salary_range": {"min": number, "max": number, "median": number, "currency": "USD"},\n'
        '"demand_level": "high" | "medium" | "low",\n'
        '"competition_level": "high" | "medium" | "low",\n'
        '"top_locations": ["location1", ...],\n'
        '"trending_skills": ["skill1", ...],\n'
        '"market_notes": "1-2 sentence summary".\n'
        "Use your knowledge of 2024-2025 tech job markets."
    )
    user_msg = f"Role: {job_title}\nSkills: {', '.join(skills)}"
    if location:
        user_msg += f"\nLocation: {location}"

    result = await chat_json(system, user_msg)
    if result:
        return result

    # Deterministic fallback
    return {
        "salary_range": {"min": 80000, "max": 180000, "median": 120000, "currency": "USD"},
        "demand_level": "medium",
        "competition_level": "medium",
        "top_locations": ["San Francisco, CA", "New York, NY", "Remote"],
        "trending_skills": skills[:5],
        "market_notes": "Market data unavailable. Showing default estimates.",
    }


def compute_skills_gap_analysis(
    contract_skills: list[str],
    candidate_skills: list[str],
) -> dict[str, Any]:
    """Detailed skills gap analysis with recommendations."""
    gap = skill_gap(contract_skills, candidate_skills)
    coverage_pct = (
        len(gap["matched"]) / len(contract_skills) * 100 if contract_skills else 0
    )

    severity = {}
    for s in gap["missing"]:
        if s in {sk.lower() for sk in contract_skills[:3]}:
            severity[s] = "critical"
        elif s in {sk.lower() for sk in contract_skills[:6]}:
            severity[s] = "important"
        else:
            severity[s] = "nice_to_have"

    return {
        "matched_skills": gap["matched"],
        "missing_skills": gap["missing"],
        "extra_skills": sorted(
            set(normalize_skills(candidate_skills)) - set(normalize_skills(contract_skills))
        ),
        "coverage_percentage": round(coverage_pct, 1),
        "skill_severity": severity,
        "recommendation": (
            "Strong fit" if coverage_pct >= 80
            else "Good fit with training needed" if coverage_pct >= 50
            else "Significant skill gap — consider training plan"
        ),
    }
