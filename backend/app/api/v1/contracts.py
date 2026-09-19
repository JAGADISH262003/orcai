from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.client import Client
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import ClientIn, ClientOut, ContractIn, ContractOut, ContractUpdateIn
from app.services.audit import audit
from app.services.jobs import run_handler_inline, submit_job

router = APIRouter(prefix="/contracts", tags=["contracts"])


def contract_to_out(c: Contract) -> ContractOut:
    return ContractOut(
        id=c.id,
        agency_id=c.agency_id,
        client_id=c.client_id,
        title=c.title,
        status=c.status,
        location=c.location,
        is_remote=c.is_remote,
        duration_months=c.duration_months,
        rate_bill=c.rate_bill,
        rate_pay=c.rate_pay,
        currency=c.currency,
        experience_min=c.experience_min,
        openings=c.openings,
        start_by=c.start_by,
        skills=c.skills or [],
        ai_summary=c.ai_summary,
        parse_method=c.parse_method,
        created_at=c.created_at,
        client_name=c.client.name if c.client else None,
    )


@router.get("", response_model=list[ContractOut])
def list_contracts(
    db: DbDep,
    agency: CurrentAgency,
    status: str | None = Query(default=None),
):
    q = db.query(Contract).filter(Contract.agency_id == agency.id)
    if status:
        q = q.filter(Contract.status == status)
    return [contract_to_out(c) for c in q.order_by(Contract.created_at.desc()).all()]


@router.post("")
async def create_contract(
    payload: ContractIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))],
    async_: bool = Query(default=True, alias="async"),
):
    """Create a contract. Parsing runs as a background job (returns 202 + JobOut)
    unless `?async=false`, which executes inline (200 + ContractOut)."""
    params = {
        "agency_id": agency.id,
        "raw_text": payload.raw_text,
        "client_name": payload.client_name,
        "client_id": payload.client_id,
    }
    audit(
        db,
        agency_id=agency.id,
        user_id=user.id,
        action="contract.create",
        meta={"async": async_},
    )
    db.commit()

    if async_:
        job = submit_job(db, agency_id=agency.id, type_="contract.parse", params=params)
        from fastapi.responses import JSONResponse

        from app.schemas.job import JobOut

        return JSONResponse(
            status_code=202,
            content=JobOut.model_validate(job).model_dump(mode="json"),
        )

    result = await run_handler_inline(db, "contract.parse", agency.id, params)
    contract = db.get(Contract, result["contract_id"])
    return contract_to_out(contract)


@router.get("/clients/list", response_model=list[ClientOut])
def list_clients(db: DbDep, agency: CurrentAgency):
    return (
        db.query(Client).filter(Client.agency_id == agency.id).order_by(Client.name.asc()).all()
    )


@router.post("/clients", response_model=ClientOut, status_code=201)
def create_client(
    payload: ClientIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))],
):
    client = Client(agency_id=agency.id, **payload.model_dump())
    db.add(client)
    db.commit()
    audit(db, agency_id=agency.id, user_id=user.id, action="client.create", entity_type="client", entity_id=client.id)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: DbDep, agency: CurrentAgency):
    c = db.get(Contract, contract_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract_to_out(c)


@router.patch("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: int,
    payload: ContractUpdateIn,
    db: DbDep,
    agency: CurrentAgency,
):
    c = db.get(Contract, contract_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return contract_to_out(c)


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: int, db: DbDep, agency: CurrentAgency):
    c = db.get(Contract, contract_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
