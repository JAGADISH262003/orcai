from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.note import Note

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteIn(BaseModel):
    entity_type: str
    entity_id: int
    content: str
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    content: str | None = None
    is_pinned: bool | None = None


def _out(n: Note) -> dict[str, Any]:
    return {
        "id": n.id,
        "agency_id": n.agency_id,
        "user_id": n.user_id,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "content": n.content,
        "is_pinned": n.is_pinned,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("")
def list_notes(
    entity_type: str,
    entity_id: int,
    user: CurrentUser,
    db: DbDep,
) -> list[dict[str, Any]]:
    q = (
        select(Note)
        .where(Note.agency_id == user.agency_id, Note.entity_type == entity_type, Note.entity_id == entity_id)
        .order_by(Note.is_pinned.desc(), Note.created_at.desc())
    )
    return [_out(r) for r in db.scalars(q).all()]


@router.post("", status_code=201)
def create_note(
    data: NoteIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    note = Note(
        agency_id=user.agency_id,
        user_id=user.id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        content=data.content,
        is_pinned=data.is_pinned,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _out(note)


@router.patch("/{note_id}")
def update_note(
    note_id: int,
    data: NoteUpdate,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    note = db.get(Note, note_id)
    if not note or note.agency_id != user.agency_id:
        raise HTTPException(404, "Note not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(note, k, v)
    db.commit()
    db.refresh(note)
    return _out(note)


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, str]:
    note = db.get(Note, note_id)
    if not note or note.agency_id != user.agency_id:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
    return {"ok": True}
