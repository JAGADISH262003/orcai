from app.services.contract_parser import find_skills, parse_contract
from app.services.dedupe import build_dedupe_key, normalize_email, normalize_phone


def test_nonexistent_skill_not_matched():
    # "go" must not match inside "Wells Fargo"
    assert "go" not in find_skills("Client: Wells Fargo. Role: Backend Engineer.")


def test_word_boundary_skill_match():
    assert find_skills("Skills: Python, Java, AWS") == ["python", "java", "aws"]


def test_pyspark_does_not_yield_spark():
    assert "spark" not in find_skills("Experience with Pyspark only")
    assert "pyspark" in find_skills("Experience with Pyspark only")


def test_parse_contract_extracts_core_fields():
    text = (
        "Client: Acme. Role: Senior Java Engineer. Requirements: Java, Spring Boot, AWS. "
        "7+ yrs exp. Rate: $85/hr. Remote. Duration 6 months."
    )
    r = parse_contract(text)
    assert r["title"] == "Senior Java Engineer"
    assert r["experience_min"] == 7
    assert r["rate_bill"] == 85.0
    assert r["is_remote"] is True
    assert r["currency"] == "USD"
    assert "java" in r["skills"]
    assert r["openings"] == 1


def test_dedupe_normalization():
    assert normalize_email("  Kiran.Kumar@EXAMPLE.COM ") == "kiran.kumar@example.com"
    assert normalize_phone("+1 (480) 555-0114") == "4805550114"
    assert build_dedupe_key("a@b.com", None, None) == "email:a@b.com"
    assert build_dedupe_key(None, "+1 123-456-7890", None) == "phone:1234567890"
    assert build_dedupe_key(None, None, "Kiran Kumar") == "name:kiran kumar"
