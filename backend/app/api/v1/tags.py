from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.seeker_tag import SeekerTag
from app.models.tag import Tag

router = APIRouter(prefix="/tags", tags=["tags"])


class TagIn(BaseModel):
    name: str
    color: str = "#5e6ad2"


def _out(t: Tag) -> dict[str, Any]:
    return {"id": t.id, "agency_id": t.agency_id, "name": t.name, "color": t.color}


@router.get("")
def list_tags(user: CurrentUser, db: DbDep) -> list[dict[str, Any]]:
    q = select(Tag).where(Tag.agency_id == user.agency_id).order_by(Tag.name)
    return [_out(t) for t in db.scalars(q).all()]


@router.post("", status_code=201)
def create_tag(data: TagIn, user: CurrentUser, db: DbDep) -> dict[str, Any]:
    existing = db.scalars(
        select(Tag).where(Tag.agency_id == user.agency_id, Tag.name == data.name)
    ).first()
    if existing:
        raise HTTPException(409, "Tag already exists")
    tag = Tag(agency_id=user.agency_id, name=data.name, color=data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _out(tag)


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    tag = db.get(Tag, tag_id)
    if not tag or tag.agency_id != user.agency_id:
        raise HTTPException(404, "Tag not found")
    db.execute(SeekerTag.__table__.delete().where(SeekerTag.tag_id == tag_id))
    db.delete(tag)
    db.commit()
    return {"ok": True}


@router.post("/seeker/{seeker_id}/attach")
def attach_tag(seeker_id: int, tag_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    tag = db.get(Tag, tag_id)
    if not tag or tag.agency_id != user.agency_id:
        raise HTTPException(404, "Tag not found")
    existing = db.scalars(
        select(SeekerTag).where(
            SeekerTag.seeker_id == seeker_id,
            SeekerTag.tag_id == tag_id,
            SeekerTag.agency_id == user.agency_id,
        )
    ).first()
    if existing:
        return {"ok": True}
    db.add(SeekerTag(seeker_id=seeker_id, tag_id=tag_id, agency_id=user.agency_id))
    db.commit()
    return {"ok": True}


@router.post("/seeker/{seeker_id}/detach")
def detach_tag(seeker_id: int, tag_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    db.execute(
        SeekerTag.__table__.delete().where(
            SeekerTag.seeker_id == seeker_id,
            SeekerTag.tag_id == tag_id,
            SeekerTag.agency_id == user.agency_id,
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/seeker/{seeker_id}")
def seeker_tags(seeker_id: int, user: CurrentUser, db: DbDep) -> list[dict[str, Any]]:
    q = (
        select(Tag)
        .join(SeekerTag, SeekerTag.tag_id == Tag.id)
        .where(SeekerTag.seeker_id == seeker_id, SeekerTag.agency_id == user.agency_id)
    )
    return [_out(t) for t in db.scalars(q).all()]
