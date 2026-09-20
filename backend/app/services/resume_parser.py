"""Resume / document text extraction and profile parsing."""

import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.services.contract_parser import SKILLS_LEXICON

logger = logging.getLogger("orcai.resume_parser")
settings = get_settings()

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-()]{8,18}\d)")
_EXP_RE = re.compile(r"(?:(\d{1,2})\s*\+?\s*years?(?:\s*of)?\s*(?:experience|exp))", re.IGNORECASE)


def extract_text_from_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        logger.warning("Failed to extract text from PDF: %s", path.name)
        return ""


def extract_text_from_docx(path: Path) -> str:
    try:
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        logger.warning("Failed to extract text from DOCX: %s", path.name)
        return ""


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    ext = settings.UPLOAD_DIR
    Path(ext).mkdir(parents=True, exist_ok=True)
    tmp = Path(ext) / ("_tmp_" + filename)
    tmp.write_bytes(content)
    try:
        if suffix == ".pdf":
            return extract_text_from_pdf(tmp)
        if suffix in (".docx", ".doc"):
            return extract_text_from_docx(tmp)
        # TXT / others
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    finally:
        tmp.unlink(missing_ok=True)


def _first_sentence(text: str) -> str:
    return text.strip().splitlines()[0][:300] if text.strip() else ""


def parse_resume_text(text: str) -> dict:
    skills = [s for s in SKILLS_LEXICON if re.search(r"\b" + re.escape(s) + r"\b", text, re.IGNORECASE)]
    email_m = _EMAIL_RE.search(text)
    phone_m = _PHONE_RE.search(text)
    exp_m = _EXP_RE.search(text)

    name = None
    for line in text.splitlines()[:6]:
        line = line.strip()
        if line and 2 <= len(line) <= 60 and not re.search(r"[\d@]|resume|cv|curriculum", line.lower()):
            name = line.split(",")[0].strip()
            break

    return {
        "name": name,
        "email": email_m.group(0) if email_m else None,
        "phone": phone_m.group(0).strip() if phone_m else None,
        "skills": skills,
        "experience_years": float(exp_m.group(1)) if exp_m else None,
        "headline": _first_sentence(text),
        "summary": text[:1500],
        "resume_text": text,
        "parse_method": "deterministic",
    }
