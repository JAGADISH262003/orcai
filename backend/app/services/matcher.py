"""Candidate–contract matching engine.

Produces an explainable score (0-100), a tier (A/B/C), and — for ambiguous
profiles — an HITL (human-in-the-loop) requirement with a rationale.
"""

import re
from typing import Any

from app.models.contract import Contract
from app.models.seeker import Seeker

# Weights
W_SKILL = 40.0
W_EXP = 20.0
W_VISA = 15.0
W_LOCATION = 10.0
W_TITLE = 15.0

# Risk-associated visa statuses (candidates that typically need more scrutiny)
RISK_VISAS = {"H1B", "OPT", "F1", "L1"}


def _score_skill(contract_skills: list[str], seeker_skills: list[str]) -> tuple[float, set[str]]:
    cset = {s.strip().lower() for s in contract_skills}
    sset = {s.strip().lower() for s in seeker_skills}
    if not cset:
        return W_SKILL * 0.7, set()
    overlap = cset & sset
    missing = cset - sset
    ratio = len(overlap) / len(cset)
    return W_SKILL * ratio, missing


def _score_experience(exp_min: int | None, exp_seeker: float | None) -> tuple[float, str | None]:
    if exp_min is None or exp_seeker is None:
        return W_EXP * 0.6, None
    if exp_seeker >= exp_min:
        return W_EXP, None
    gap = exp_min - exp_seeker
    if gap <= 1:
        return W_EXP * 0.6, f"{gap:.0f}yr short of required {exp_min}yr experience"
    return W_EXP * 0.2, f"{gap:.0f}yr short of required {exp_min}yr experience"


def _score_visa(visa: str | None) -> tuple[float, bool]:
    if not visa:
        return W_VISA * 0.6, False
    v = visa.upper()
    if v in ("GC", "GREEN CARD", "CITIZEN", "US CITIZEN", "GC EAD"):
        return W_VISA, False
    if v in ("H1B", "OPT"):
        return W_VISA * 0.6, True  # transfer sponsorship usually required
    if v in ("TN", "L1", "EAD"):
        return W_VISA * 0.8, True
    return W_VISA * 0.7, False


def _score_title(ctitle: str | None, headline: str | None, skills: list[str]) -> float:
    if not ctitle:
        return W_TITLE * 0.6
    text = (headline or "").lower() + " " + " ".join(skills)
    words = [w for w in ctitle.lower().replace("/", " ").split() if len(w) > 2]
    hits = sum(1 for w in words if w in text)
    if not words:
        return W_TITLE * 0.6
    ratio = min(1.0, hits / len(words) + 0.3)
    return W_TITLE * ratio


def _score_location(contract_location: str | None, contract_remote: bool | None, seeker_location: str | None) -> float:
    if contract_remote:
        return W_LOCATION
    if not contract_location or not seeker_location:
        return W_LOCATION * 0.6
    if contract_location.lower() in seeker_location.lower():
        return W_LOCATION
    return W_LOCATION * 0.4


def _detect_gaps(resume_text: str | None) -> list[str]:
    """Return risk signals found in resume text (gap years, unclear employment)."""
    signals: list[str] = []
    if not resume_text:
        return signals
    low = resume_text.lower()
    m = re.search(r"(\d{4})\s*[-–—]\s*(\d{4})", resume_text)
    if m:
        y1, y2 = int(m.group(1)), int(m.group(2))
        if y2 - y1 > 4:
            signals.append("long single employment span detected, verify continuity")
    if "freelanc" in low and "gap" not in signals:
        signals.append("freelance history present; verify client references")
    if "career break" in low:
        signals.append("career break mentioned in resume")
    return signals


def compute_match(
    contract: Contract, seeker: Seeker, *, entry_status: str = "pending"
) -> dict[str, Any]:
    skill_pts, missing = _score_skill(contract.skills or [], seeker.skills or [])
    exp_pts, exp_note = _score_experience(contract.experience_min, seeker.experience_years)
    visa_pts, visa_risk = _score_visa(seeker.visa_status)
    loc_pts = _score_location(contract.location, contract.is_remote, seeker.location)
    title_pts = _score_title(contract.title, seeker.headline, seeker.skills or [])

    score = round(skill_pts + exp_pts + visa_pts + loc_pts + title_pts, 1)
    score = max(0.0, min(100.0, score))

    tier = "A" if score >= 85 else ("B" if score >= 65 else "C")

    # HITL heuristics: only genuinely uncertain, reviewable matches (55-84) enter
    # the human loop. Very weak matches (Tier C) are auto-filtered instead.
    signals = _detect_gaps(seeker.resume_text)
    reasons: list[str] = []
    if missing:
        reasons.append(f"missing sought skills: {', '.join(sorted(missing)[:4])}")
    if visa_risk:
        reasons.append(f"visa status {seeker.visa_status} — verify sponsorship availability")
    if exp_note:
        reasons.append(exp_note)
    reasons.extend(signals)

    hitl_required = bool(reasons) and 55 <= score < 85
    rationale = None
    if hitl_required:
        rationale = (
            f"AI uncertainty (score {score:.0f}%, tier {tier}): " + "; ".join(reasons) + "."
        )
    elif score >= 85:
        rationale = "High-confidence match — no manual review required."

    # Default pipeline status suggestion (entry stage of the tenant's workflow).
    default_status = entry_status if score >= 55 else "rejected"

    return {
        "score": score,
        "tier": tier,
        "hitl_required": hitl_required,
        "rationale": rationale,
        "missing_skills": sorted(missing),
        "default_status": default_status,
    }
