import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.document import Document

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("uploads")


class DocumentOut(BaseModel):
    id: int
    agency_id: int
    uploaded_by: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    entity_type: str | None
    entity_id: int | None
    description: str | None
    created_at: str | None
    updated_at: str | None


def _out(d: Document) -> dict[str, Any]:
    return {
        "id": d.id,
        "agency_id": d.agency_id,
        "uploaded_by": d.uploaded_by,
        "filename": d.filename,
        "original_filename": d.original_filename,
        "file_path": d.file_path,
        "file_size": d.file_size,
        "mime_type": d.mime_type,
        "entity_type": d.entity_type,
        "entity_id": d.entity_id,
        "description": d.description,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


@router.get("")
def list_documents(
    user: CurrentUser,
    db: DbDep,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    q = select(Document).where(Document.agency_id == user.agency_id)
    if entity_type:
        q = q.where(Document.entity_type == entity_type)
    if entity_id:
        q = q.where(Document.entity_id == entity_id)
    q = q.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    return [_out(r) for r in db.scalars(q).all()]


@router.post("/upload", status_code=201)
async def upload_document(
    user: CurrentUser,
    db: DbDep,
    file: UploadFile = File(...),  # noqa: B008
    entity_type: str | None = Form(None),
    entity_id: int | None = Form(None),
    description: str | None = Form(None),
) -> dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / safe_name
    content = await file.read()
    file_path.write_bytes(content)

    doc = Document(
        agency_id=user.agency_id,
        uploaded_by=user.id,
        filename=safe_name,
        original_filename=file.filename or "file",
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _out(doc)


@router.get("/{document_id}")
def get_document(
    document_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    doc = db.get(Document, document_id)
    if not doc or doc.agency_id != user.agency_id:
        raise HTTPException(404, "Document not found")
    return _out(doc)


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    user: CurrentUser,
    db: DbDep,
) -> FileResponse:
    doc = db.get(Document, document_id)
    if not doc or doc.agency_id != user.agency_id:
        raise HTTPException(404, "Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(404, "File not found on disk")
    return FileResponse(
        path=doc.file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, str]:
    doc = db.get(Document, document_id)
    if not doc or doc.agency_id != user.agency_id:
        raise HTTPException(404, "Document not found")
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"ok": True}
