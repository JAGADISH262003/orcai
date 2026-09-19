"""Access + refresh token lifecycle with server-side rotation and revocation."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.mixins import utcnow
from app.models.refresh_token import RefreshToken
from app.models.user import User

settings = get_settings()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_access(user: User) -> str:
    return create_access_token(str(user.id), user.agency_id, user.role)


def issue_refresh(
    db: Session, user: User, *, ip: str | None = None, user_agent: str | None = None
) -> tuple[str, RefreshToken]:
    """Issue a new refresh token (stored hashed). Returns (raw_token, record)."""
    token = secrets.token_urlsafe(48)
    record = RefreshToken(
        agency_id=user.agency_id,
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        created_by_ip=ip,
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(record)
    db.flush()
    return token, record


def rotate_refresh(
    db: Session,
    old_token: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, RefreshToken] | None:
    """Validate an existing refresh token, revoke it, and issue a replacement.

    Returns (new_raw_token, user) on success, None if invalid/expired/revoked.
    """
    record = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(old_token)).first()
    )
    if record is None or record.revoked or record.expires_at < utcnow():
        return None
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        return None

    # Rotate: revoke old, mint new, chain them.
    record.revoked = True
    record.revoked_at = utcnow()
    new_token, new_record = issue_refresh(db, user, ip=ip, user_agent=user_agent)
    record.replaced_by_id = new_record.id
    return new_token, user


def revoke_refresh(db: Session, token: str) -> bool:
    record = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(token)).first()
    )
    if record is None or record.revoked:
        return False
    record.revoked = True
    record.revoked_at = utcnow()
    return True
