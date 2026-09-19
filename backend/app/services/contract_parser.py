"""Contract / requisition parsing.

Structured output produced deterministically — and optionally LLM-assisted
when OPENAI_API_KEY is configured (LLM refines fields it is confident about).
"""

import re
from typing import Any

from app.services.llm import chat_json

SKILLS_LEXICON = [
    # Languages
    "python", "java", "javascript", "typescript", "go", "golang", "ruby", "c#", "c++",
    "csharp", "kotlin", "swift", "scala", "rust", "php", "sql",
    # Frontend
    "react", "react native", "angular", "vue", "next.js", "nextjs", "redux", "html", "css",
    "sass", "tailwind", "webpack", "gatsby", "graphql",
    # Backend / frameworks
    "spring boot", "spring", "django", "flask", "fastapi", "node.js", "nodejs", "express",
    "hibernate", "microservices", "rest api", "restful", "soap", "kafka", "rabbitmq",
    # Data / Big Data
    "sql", "postgresql", "mysql", "mongodb", "nosql", "oracle", "redis", "snowflake",
    "spark", "hadoop", "pyspark", "databricks", "airflow", "etl", "dbt", "tableau", "power bi",
    "elasticsearch", "data engineering", "data warehouse", "datalake", "bigquery",
    # AI / ML
    "machine learning", "deep learning", "llm", "nlp", "pytorch", "tensorflow", "keras",
    "computer vision", "rag", "langchain", "openai", "genai", "generative ai", "prompt engineering",
    "scikit-learn", "pandas", "numpy",
    # Cloud / DevOps / SRE
    "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s", "docker", "terraform",
    "ansible", "jenkins", "ci/cd", "gitlab ci", "github actions", "linux", "nginx",
    "prometheus", "grafana", "splunk", "opentelemetry", "sre", "devops", "cloudformation",
    # Mobile
    "react native", "flutter", "android", "ios", "xamarin",
    # Security
    "security", "cybersecurity", "penetration testing", "siem", "iam", "iso 27001",
    "soc", "compliance", "grc", "vulnerability",
    # QA
    "qa", "selenium", "cypress", "playwright", "junit", "pytest", "test automation", "manual testing",
    # Project / Functional
    "agile", "scrum", "kanban", "product management", "stakeholder management", "pmp",
    "servicenow", "sap", "salesforce", "workday", "mainframe", "cobol", "sas",
]

_RATE_RE = re.compile(
    r"(?P<cur>\$|₹|€|£)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:/\s*(?:hr|hour))?",
    re.IGNORECASE,
)
_EXP_RE = re.compile(r"(\d{1,2})\s*\+\s*(?:years|yrs|yr)", re.IGNORECASE)
_OPENINGS_RE = re.compile(r"(?:opening|positions?|headcount|slots?)\s*[:=]?\s*(\d+)", re.IGNORECASE)
_DURATION_RE = re.compile(r"duration\s*[:=]?\s*(\d+)\s*(?:months?|m)", re.IGNORECASE)


def _norm(text: str) -> str:
    return text.lower()


def find_skills(text: str) -> list[str]:
    found: list[str] = []
    for skill in SKILLS_LEXICON:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text, re.IGNORECASE) and skill not in found:
            found.append(skill)
    return found


def _extract_rates(text: str) -> tuple[float | None, float | None, str]:
    matches = _RATE_RE.findall(text)
    if not matches:
        return None, None, "USD"
    values = []
    for cur, num in matches:
        values.append((cur, float(num.replace(",", ""))))
    # First (currency, value) wins; if two values present, treat as bill / pay.
    currency = values[0][0]
    currency = {"$": "USD", "₹": "INR", "€": "EUR", "£": "GBP"}.get(currency, "USD")
    bill = values[0][1]
    pay = values[1][1] if len(values) > 1 else None
    return bill, pay, currency


def _extract_location(text: str) -> tuple[str | None, bool | None]:
    low = _norm(text)
    if "remote" in low:
        return ("Remote", True)
    if "hybrid" in low:
        return ("Hybrid", False)
    # Heuristic: "Onsite - City, State" / "Location: X"
    m = re.search(r"location\s*[:=]\s*([A-Za-z ,\-]{3,40})", low)
    if m:
        return (m.group(1).strip().title(), False)
    m = re.search(r"onsite\s*[-–]\s*([A-Za-z ,\-]{3,40})", low)
    if m:
        return (m.group(1).strip().title(), False)
    return None, None


def extract_title(text: str) -> str | None:
    patterns = [
        r"(?:role|job ?title|position|requisition(?: title)?)\s*[:=]\s*([^\n.!?;]{3,80})",
        r"^\s*([A-Z][^\n]{3,60})\s*$",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().strip(":;-.")
            if 3 <= len(cand) <= 80:
                return cand
    return None


def _extract_duration(text: str) -> int | None:
    m = _DURATION_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def _build_summary(title, loc, remote, skills, exp_m, bill, pay, currency, duration):
    parts = []
    if title:
        parts.append(f"{title} role")
    if loc:
        parts.append(f"located in {loc}" + (" (remote)" if remote else ""))
    elif remote:
        parts.append("remote position")
    if exp_m:
        parts.append(f"requiring {exp_m.group(1)}+ years of experience")
    if skills:
        parts.append(f"key skills: {', '.join(skills[:5])}")
    if bill and pay:
        parts.append(f"bill rate {currency or 'USD'} {bill}/hr, pay rate {currency or 'USD'} {pay}/hr")
    elif bill:
        parts.append(f"rate {currency or 'USD'} {bill}/hr")
    if duration:
        parts.append(f"duration: {duration} months")
    return ". ".join(parts).capitalize() + "." if parts else None


def parse_contract(text: str) -> dict[str, Any]:
    """Deterministic extractor. Returns a structure identical to the AI schema."""
    bill, pay, currency = _extract_rates(text)
    exp_m = _EXP_RE.search(text)
    open_m = _OPENINGS_RE.search(text)
    loc, remote = _extract_location(text)
    title = extract_title(text)
    skills = find_skills(text)
    duration = _extract_duration(text)
    summary = _build_summary(title, loc, remote, skills, exp_m, bill, pay, currency, duration)

    return {
        "title": title,
        "location": loc,
        "is_remote": remote,
        "duration_months": duration,
        "rate_bill": bill,
        "rate_pay": pay,
        "currency": currency,
        "experience_min": int(exp_m.group(1)) if exp_m else None,
        "openings": int(open_m.group(1)) if open_m else 1,
        "skills": skills,
        "ai_summary": summary,
        "parse_method": "deterministic",
    }


async def parse_contract_with_ai(text: str) -> dict[str, Any]:
    """Parse a contract, using LLM first then merging with deterministic fallback."""
    base = parse_contract(text)

    system = (
        "You are a recruiting contract extractor. Return a JSON object with keys: "
        "title, location, is_remote (bool or null), duration_months (int or null), "
        "rate_bill (float or null, client bill rate), rate_pay (float or null, candidate pay), "
        "currency (3-letter code), experience_min (int or null), openings (int), "
        "skills (array of lowercase strings), ai_summary (1-2 sentence summary). "
        "If a field is unknown, use null. Do not invent values."
    )
    result = await chat_json(system, f"Contract text:\n\n{text[:6000]}")
    if result is None:
        return base

    merged = {
        "title": result.get("title") or base["title"],
        "location": result.get("location") or base["location"],
        "is_remote": result.get("is_remote") if result.get("is_remote") is not None else base["is_remote"],
        "duration_months": result.get("duration_months") or base["duration_months"],
        "rate_bill": result.get("rate_bill") or base["rate_bill"],
        "rate_pay": result.get("rate_pay") or base["rate_pay"],
        "currency": (result.get("currency") or base["currency"] or "USD").upper(),
        "experience_min": result.get("experience_min") or base["experience_min"],
        "openings": result.get("openings") or base["openings"] or 1,
        "skills": result.get("skills") or base["skills"],
        "ai_summary": result.get("ai_summary"),
        "parse_method": "ai",
    }
    return merged
