"""Enterprise-layer tests: RBAC enforcement, multi-tenancy isolation, job
lifecycle, refresh-token rotation, audit trail, and rate limiting."""

from itertools import count

import pytest

from app.core.security import hash_password
from app.models.agency import Agency
from app.models.audit import AuditLog
from app.models.user import User

PWD = "TestPass@123"

_SEQ = count(1)


def _seed_agency(db, name: str, role: str, email_tag: str):
    n = next(_SEQ)
    agency = Agency(name=name, slug=f"{email_tag}-{n}")
    db.add(agency)
    db.flush()
    email = f"{email_tag}-{n}@test.io"
    user = User(
        agency_id=agency.id,
        email=email,
        name=f"{role.title()} {name}",
        role=role,
        hashed_password=hash_password(PWD),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return agency, user, email


def _login(client, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PWD}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def two_agencies(db, client):
    a, _a_owner, a_owner_email = _seed_agency(db, "Alpha Co", "owner", "owneralpha")
    _a_recruiter, _ar, recruiter_email = _seed_agency(db, "Alpha Co", "recruiter", "recralpha")
    b, _b_owner, b_owner_email = _seed_agency(db, "Beta Co", "owner", "ownerbeta")
    _cuser, _cu, client_email = _seed_agency(db, "Beta Co", "client", "clientbeta")

    a_owner_login = _login(client, a_owner_email)
    a_recruiter_tok = _login(client, recruiter_email)["access_token"]
    b_owner_tok = _login(client, b_owner_email)["access_token"]
    client_tok = _login(client, client_email)["access_token"]

    return {
        "a": a,
        "b": b,
        "a_owner_tok": a_owner_login["access_token"],
        "a_owner_refresh": a_owner_login["refresh_token"],
        "a_recruiter_tok": a_recruiter_tok,
        "b_owner_tok": b_owner_tok,
        "client_tok": client_tok,
    }


def test_recruiter_denied_billing_hitl_consent(client, two_agencies):
    tt = two_agencies
    tok = tt["a_recruiter_tok"]

    # recruiter CAN create contracts
    r = client.post(
        "/api/v1/contracts?async=false",
        headers=_h(tok),
        json={"raw_text": "Client X. Role: Analyst. Skills: Excel.", "client_name": "XCorp"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] >= 1

    # recruiter DENIED billing plan change
    r = client.post("/api/v1/billing/subscription/select/growth", headers=_h(tok))
    assert r.status_code == 403, r.text

    # recruiter DENIED consent erase (settings.write)
    r = client.post("/api/v1/consent/999/erase", headers=_h(tok))
    assert r.status_code == 403, r.text

    # recruiter DENIED team management
    r = client.get("/api/v1/auth/users", headers=_h(tok))
    assert r.status_code == 403, r.text

    # owner CAN do all of those
    r = client.post(
        "/api/v1/billing/subscription/select/growth", headers=_h(tt["a_owner_tok"])
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/auth/users", headers=_h(tt["a_owner_tok"]))
    assert r.status_code == 200, r.text


def test_client_role_read_only(client, two_agencies):
    tok = two_agencies["client_tok"]
    r = client.post(
        "/api/v1/contracts", headers=_h(tok), json={"raw_text": "Role X"}
    )
    assert r.status_code == 403, r.text
    r = client.get("/api/v1/contracts", headers=_h(tok))
    assert r.status_code == 200, r.text


def test_tenancy_isolation(client, db, two_agencies):
    tt = two_agencies
    # Agency A creates a contract + seeker + match (inline)
    r = client.post(
        "/api/v1/contracts?async=false",
        headers=_h(tt["a_owner_tok"]),
        json={
            "raw_text": "Client Acme. Role: Backend Engineer. Bangalore. Hybrid. "
                        "Skills: Python, FastAPI, SQL. Rate INR 25L.",
            "client_name": "Acme",
        },
    )
    assert r.status_code == 200, r.text
    a_contract_id = r.json()["id"]

    s = client.post(
        "/api/v1/seekers",
        headers=_h(tt["a_owner_tok"]),
        json={
            "name": "Alpha Candidate",
            "email": "cand@alpha.io",
            "phone": "+919800000001",
            "skills": ["Python", "SQL"],
            "experience_years": 4,
        },
    )
    assert s.status_code == 201, s.text

    r = client.post("/api/v1/matches/run?async=false", headers=_h(tt["a_owner_tok"]))
    assert r.status_code == 200, r.text
    a_matches = r.json()

    # Agency B cannot read A's resources
    for path in (
        f"/api/v1/contracts/{a_contract_id}",
        f"/api/v1/matches/{a_matches[0]['id']}",
    ):
        resp = client.get(path, headers=_h(tt["b_owner_tok"]))
        assert resp.status_code == 404, (path, resp.status_code, resp.text[:100])

    # Agency B's seeker search does not leak A's candidates
    r = client.get("/api/v1/seekers?q=Alpha", headers=_h(tt["b_owner_tok"]))
    assert r.status_code == 200, r.text
    names = [x["name"] for x in r.json()]
    assert "Alpha Candidate" not in names


def test_job_lifecycle_and_tenancy(client, db, two_agencies):
    tt = two_agencies
    r = client.post(
        "/api/v1/contracts?async=true",
        headers=_h(tt["a_owner_tok"]),
        json={"raw_text": "Client Z. Role: DevOps. Skills: AWS, Docker."},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    assert r.json()["type"] == "contract.parse"
    assert r.json()["status"] == "pending"

    # drain the queue (equates to the in-process/standalone worker claiming + running)
    import asyncio

    from app.services.jobs import process_available

    asyncio.run(process_available(db))

    g = client.get(f"/api/v1/jobs/{job_id}", headers=_h(tt["a_owner_tok"]))
    assert g.status_code == 200, g.text
    assert g.json()["status"] == "done", g.text
    assert g.json()["result"]["contract_id"] >= 1

    # cross-agency job access is forbidden
    r = client.get(f"/api/v1/jobs/{job_id}", headers=_h(tt["b_owner_tok"]))
    assert r.status_code == 404, r.text


def test_refresh_token_rotation_and_revocation(client, db, two_agencies):
    tt = two_agencies
    refresh = tt["a_owner_refresh"]
    assert refresh

    # first refresh rotates the token and works
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    new_refresh = r.json()["refresh_token"]
    assert new_refresh and new_refresh != refresh

    # the old token is now revoked
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code in (400, 401), r.text

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert r.status_code == 200, r.text

    # logout revokes the family
    r = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert r.status_code == 204, r.text
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert r.status_code in (400, 401), r.text


def test_audit_trail_written(client, db, two_agencies):
    tt = two_agencies
    before = db.query(AuditLog).count()
    client.post(
        "/api/v1/contracts?async=false",
        headers=_h(tt["a_owner_tok"]),
        json={"raw_text": "Client Q. Role: PM. Skills: Jira.", "client_name": "QCo"},
    )
    after = db.query(AuditLog).count()
    assert after > before
    actions = {a.action for a in db.query(AuditLog).all()}
    assert "contract.create" in actions
    assert "auth.login" in actions


def test_rate_limit_429(client):
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.RL_ENABLED
    settings.RL_ENABLED = True
    try:
        codes = [
            client.get("/api/v1/seekers").status_code
            for _ in range(60)
        ]
        assert 429 in codes, f"expected a 429 among {codes.count(200)}x200"
    finally:
        settings.RL_ENABLED = original
