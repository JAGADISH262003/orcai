"""Workflow engine tests: catalog, registration selection, entry stages, status validation."""

from app.core.workflows import DEFAULT_WORKFLOW, WORKFLOWS, pipeline_stages, valid_match_statuses
from app.models.client import Client
from app.models.contract import Contract
from app.models.match import Match
from app.models.seeker import Seeker


def _register(client, email, workflow_type=None):
    payload = {
        "agency_name": f"WF {email.split('@')[0]}",
        "name": "Owner",
        "email": email,
        "password": "password123",
    }
    if workflow_type is not None:
        payload["workflow_type"] = workflow_type
    return client.post("/api/v1/auth/register", json=payload)


def _make_contract_and_seeker(db, agency_id):
    client = Client(agency_id=agency_id, name="Acme")
    db.add(client)
    db.flush()
    contract = Contract(
        agency_id=agency_id,
        client_id=client.id,
        title="Senior Data Engineer",
        status="active",
        is_remote=True,
        duration_months=6,
        rate_bill=85,
        rate_pay=65,
        currency="USD",
        experience_min=3,
        openings=1,
        skills=["python", "sql"],
        ai_summary="Strong data engineering profile needed.",
        parse_method="deterministic",
        raw_text="Python, SQL, ETL. 3+ yrs.",
    )
    seeker = Seeker(
        agency_id=agency_id,
        name="Jane Doe",
        email=f"jane{agency_id}@example.com",
        phone=None,
        visa_status="GC EAD",
        location="Remote",
        headline="Senior Data Engineer",
        skills=["python", "sql", "aws"],
        experience_years=6.0,
        summary="Strong data engineer.",
        resume_text="Senior Data Engineer. Python, SQL. GC EAD.",
        is_active=True,
    )
    db.add_all([contract, seeker])
    db.flush()
    return contract, seeker


def test_catalog_lists_all_workflows(client):
    r = client.get("/api/v1/workflows")
    assert r.status_code == 200
    data = r.json()
    assert data["default"] == DEFAULT_WORKFLOW
    assert len(data["workflows"]) == len(WORKFLOWS)
    keys = {w["key"] for w in data["workflows"]}
    assert keys == set(WORKFLOWS)


def test_register_defaults_to_domestic_it(client):
    r = _register(client, "wfdefault@b.com")
    assert r.status_code == 201
    data = r.json()
    assert data["agency"]["workflow_type"] == "domestic_it"
    wf = data["agency"]["workflow"]
    assert wf["entry_stage"] == "pending"
    assert wf["fill_stage"] == "placed"
    assert [s["key"] for s in wf["stages"]] == ["pending", "approved", "submitted", "placed"]


def test_register_with_us_bench_sales_workflow(client):
    r = _register(client, "wfbench@b.com", workflow_type="us_bench_sales")
    assert r.status_code == 201
    data = r.json()
    assert data["agency"]["workflow_type"] == "us_bench_sales"
    wf = data["agency"]["workflow"]
    assert wf["entry_stage"] == "bench"
    assert wf["fill_stage"] == "on_project"
    keys = [s["key"] for s in wf["stages"]]
    assert "hotlisted" in keys and "rtr_signed" in keys and "on_project" in keys


def test_register_invalid_workflow_rejected(client):
    r = _register(client, "wfbad@b.com", workflow_type="nope")
    assert r.status_code == 400
    assert "workflow_type" in r.json()["detail"]


def test_me_materialises_workflow_config(client, db):
    r = _register(client, "wfme@b.com", workflow_type="exec_search")
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    wf = me.json()["agency"]["workflow"]
    assert wf["entry_stage"] == "mandate"
    agency_id = me.json()["agency"]["id"]
    from app.models.agency import Agency

    stored = db.get(Agency, agency_id)
    assert stored.workflow_config["key"] == "exec_search"
    assert stored.workflow_config["stages"][0]["key"] == "mandate"


def test_pipeline_stages_helpers():
    assert pipeline_stages("domestic_it")[0]["key"] == "pending"
    assert "bench" in valid_match_statuses("us_bench_sales")
    assert "rejected" in valid_match_statuses("us_bench_sales")
    assert "pending" not in valid_match_statuses("us_bench_sales")


def test_match_status_validated_against_workflow(client, db):
    r = _register(client, "wfstat@b.com", workflow_type="us_bench_sales")
    token = r.json()["access_token"]
    agency_id = r.json()["agency"]["id"]
    contract, seeker = _make_contract_and_seeker(db, agency_id)
    db.commit()

    match = Match(agency_id=agency_id, contract_id=contract.id, seeker_id=seeker.id,
                  score=88.0, tier="A", status="bench", hitl_required=False)
    db.add(match)
    db.commit()
    db.refresh(match)
    mid = match.id

    headers = {"Authorization": f"Bearer {token}"}
    bogus = client.patch(f"/api/v1/matches/{mid}/status", json={"status": "placed"}, headers=headers)
    assert bogus.status_code == 400

    ok = client.patch(f"/api/v1/matches/{mid}/status", json={"status": "hotlisted"}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["status"] == "hotlisted"


def test_matching_entry_status_uses_workflow(client, db):
    r = _register(client, "wfentry@b.com", workflow_type="us_bench_sales")
    token = r.json()["access_token"]
    agency_id = r.json()["agency"]["id"]
    contract, _seeker = _make_contract_and_seeker(db, agency_id)
    db.commit()

    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(f"/api/v1/matches/run?contract_id={contract.id}&async=false", headers=headers)
    assert res.status_code == 200
    rows = res.json()
    assert rows and all(m["status"] == "bench" for m in rows)
