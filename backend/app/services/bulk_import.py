"""Tier 2 Consultancy DB Migration: bulk CSV/ZIP import with column mapping wizard.

The "moat" feature from the docs — lets recruitment consultancies import their
existing candidate databases (CSV/ZIP of CSVs) with intelligent column mapping
and DPDPA consent handling.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from typing import Any

from sqlalchemy.orm import Session

from app.services.seeker_ingest import upsert_seeker

logger = logging.getLogger("orcai.bulk_import")

# Standard column aliases: maps common header variations to our internal fields.
COLUMN_ALIASES: dict[str, list[str]] = {
    "name": ["name", "full_name", "candidate_name", "candidate", "applicant_name", "applicant", "first_name", "fname"],
    "email": ["email", "email_address", "e-mail", "mail", "contact_email"],
    "phone": ["phone", "phone_number", "mobile", "contact_number", "telephone", "cell"],
    "visa_status": ["visa", "visa_status", "work_authorization", "authorization", "visa_type", "immigration_status"],
    "location": ["location", "city", "address", "current_location", "region", "area", "place"],
    "headline": ["headline", "title", "designation", "current_title", "job_title", "position", "role"],
    "skills": ["skills", "skill_set", "technical_skills", "competencies", "technologies", "tech_stack"],
    "experience_years": ["experience", "years_of_experience", "yoe", "exp", "total_experience", "work_experience"],
    "summary": ["summary", "about", "bio", "description", "profile_summary", "objective"],
    "education": ["education", "degree", "qualification", "academic", "university"],
    "linkedin_url": ["linkedin", "linkedin_url", "linkedin_profile", "linkedin_link"],
}


def _detect_columns(headers: list[str]) -> dict[str, int | None]:
    """Auto-detect mapping from CSV headers to our standard fields."""
    mapping: dict[str, int | None] = {field: None for field in COLUMN_ALIASES}
    header_lower = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in headers]

    for field, aliases in COLUMN_ALIASES.items():
        for idx, h in enumerate(header_lower):
            if h in aliases or any(a in h for a in aliases):
                mapping[field] = idx
                break
    return mapping


def _parse_skills_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    # Split by common delimiters
    parts = re.split(r"[,;|/]+", raw)
    return [s.strip().lower() for s in parts if s.strip() and len(s.strip()) > 1]


def _parse_experience(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    return float(m.group(1)) if m else None


def preview_csv(file_content: str | bytes, encoding: str = "utf-8") -> dict:
    """Parse a CSV and return a preview with auto-detected column mapping.

    Returns: {
        "headers": [...],
        "total_rows": int,
        "preview_rows": [ {...}, ... ],
        "auto_mapping": { field: header_name | null },
        "sample_data": [ {...}, ... ]
    }
    """
    if isinstance(file_content, bytes):
        text = file_content.decode(encoding, errors="replace")
    else:
        text = file_content

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"headers": [], "total_rows": 0, "preview_rows": [], "auto_mapping": {}, "sample_data": []}

    headers = rows[0]
    data_rows = rows[1:]
    mapping = _detect_columns(headers)

    # Build preview
    preview_rows = []
    for row in data_rows[:5]:
        record = {}
        for field, idx in mapping.items():
            record[field] = row[idx] if idx is not None and idx < len(row) else None
        preview_rows.append(record)

    auto_mapping = {}
    for field, idx in mapping.items():
        auto_mapping[field] = headers[idx] if idx is not None and idx < len(headers) else None

    return {
        "headers": headers,
        "total_rows": len(data_rows),
        "preview_rows": preview_rows,
        "auto_mapping": auto_mapping,
        "sample_data": preview_rows,
    }


def import_csv(
    db: Session,
    agency_id: int,
    file_content: str | bytes,
    mapping: dict[str, int] | None = None,
    encoding: str = "utf-8",
    consent_basis: str = "affidavit",
    source_label: str = "bulk_import",
) -> dict:
    """Import a CSV file into the seeker pool.

    Args:
        mapping: Explicit column mapping {field: column_index}. If None, auto-detect.

    Returns: {
        "imported": int,
        "skipped": int,
        "errors": int,
        "details": [...]
    }
    """
    if isinstance(file_content, bytes):
        text = file_content.decode(encoding, errors="replace")
    else:
        text = file_content

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"imported": 0, "skipped": 0, "errors": 0, "details": []}

    headers = rows[0]
    data_rows = rows[1:]

    if mapping is None:
        mapping = _detect_columns(headers)

    imported = 0
    skipped = 0
    errors = 0
    details = []

    for row_num, row in enumerate(data_rows, start=2):
        try:
            data: dict[str, Any] = {}
            for field, idx in mapping.items():
                if idx is not None and idx < len(row):
                    data[field] = row[idx]
                else:
                    data[field] = None

            # Skip empty rows
            if not data.get("name") and not data.get("email"):
                skipped += 1
                continue

            # Parse skills
            if isinstance(data.get("skills"), str):
                data["skills"] = _parse_skills_field(data["skills"])
            else:
                data["skills"] = []

            # Parse experience
            data["experience_years"] = _parse_experience(data.get("experience_years"))

            seeker, created = upsert_seeker(
                db,
                agency_id,
                data,
                source=source_label,
                source_channel="bulk_csv",
                consent_basis=consent_basis,
                consent_channel="file_upload",
            )
            imported += 1
            details.append({"row": row_num, "status": "imported", "seeker_id": seeker.id, "name": data.get("name")})

        except Exception as exc:
            errors += 1
            details.append({"row": row_num, "status": "error", "error": str(exc)})
            logger.warning("Row %d import error: %s", row_num, exc)

    db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors, "details": details}


def import_zip(
    db: Session,
    agency_id: int,
    zip_bytes: bytes,
    mapping: dict[str, int] | None = None,
    consent_basis: str = "affidavit",
) -> dict:
    """Import a ZIP file containing multiple CSVs."""
    total_imported = 0
    total_skipped = 0
    total_errors = 0
    files_processed = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_files = [f for f in zf.namelist() if f.lower().endswith(".csv")]
            for csv_name in csv_files:
                csv_content = zf.read(csv_name)
                result = import_csv(
                    db, agency_id, csv_content,
                    mapping=mapping,
                    consent_basis=consent_basis,
                    source_label=f"bulk_zip:{csv_name}",
                )
                total_imported += result["imported"]
                total_skipped += result["skipped"]
                total_errors += result["errors"]
                files_processed.append({"file": csv_name, **result})
    except zipfile.BadZipFile:
        return {"imported": 0, "skipped": 0, "errors": 1, "files": [], "error": "Invalid ZIP file"}

    return {
        "imported": total_imported,
        "skipped": total_skipped,
        "errors": total_errors,
        "files": files_processed,
    }
