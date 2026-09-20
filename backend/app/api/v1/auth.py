import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import CurrentUser, DbDep, OwnerOrAdmin, bearer_scheme
from app.core.config import get_settings
from app.core.rbac import VALID_ROLES
from app.core.security import (
    authenticate_user,
    create_password_reset_token,
    decode_access_token,
    hash_password,
)
from app.core.workflows import WORKFLOWS
from app.models.agency import Agency
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.auth import (
    AgencyOut,
    InviteIn,
    InviteOut,
    LoginIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserOut,
    UserUpdateIn,
    user_to_out,
)
from app.services.audit import audit
from app.services.auth_tokens import (
    issue_access,
    issue_refresh,
    revoke_refresh,
    rotate_refresh,
)

logger = logging.getLogger("orcai.auth")

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:40] or f"agency-{secrets.randbelow(100000)}"


def _unique_slug(db, name: str) -> str:
    slug = _slugify(name)
    if db.query(Agency).filter(Agency.slug == slug).first() is None:
        return slug
    return f"{slug}-{secrets.token_hex(3)}"


def _client_ctx(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, (request.headers.get("user-agent") or "")[:300]


def _token_response(db, user: User, *, refresh: str | None = None, ip: str | None = None, user_agent: str | None = None) -> TokenOut:
    access = issue_access(user)
    if refresh is None:
        refresh, _ = issue_refresh(db, user, ip=ip, user_agent=user_agent)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_to_out(user),
        agency=AgencyOut.model_validate(user.agency),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, request: Request, db: DbDep):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if payload.workflow_type and payload.workflow_type not in WORKFLOWS:
        raise HTTPException(
            status_code=400,
            detail=f"workflow_type must be one of {sorted(WORKFLOWS)}",
        )

    agency = Agency(
        name=payload.agency_name,
        slug=_unique_slug(db, payload.agency_name),
        tier="starter",
        workflow_type=payload.workflow,
    )
    db.add(agency)
    db.flush()
    agency.ensure_workflow_config()

    user = User(
        agency_id=agency.id,
        email=email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role="owner",
        is_active=True,
    )
    db.add(user)

    today = datetime.now(UTC).date()
    db.add(
        Subscription(
            agency_id=agency.id,
            tier="starter",
            price_per_month=4999,
            billing_cycle_start=today,
            billing_cycle_end=today + timedelta(days=30),
            status="trialing",
            seats=3,
        )
    )
    db.flush()
    ip, ua = _client_ctx(request)
    response = _token_response(db, user, ip=ip, user_agent=ua)
    audit(db, agency_id=agency.id, user_id=user.id, action="auth.register", ip=ip)
    db.commit()
    return response


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: DbDep):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    db.refresh(user)
    ip, ua = _client_ctx(request)
    response = _token_response(db, user, ip=ip, user_agent=ua)
    audit(db, agency_id=user.agency_id, user_id=user.id, action="auth.login", ip=ip)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, request: Request, db: DbDep):
    ip, ua = _client_ctx(request)
    rotated = rotate_refresh(db, payload.refresh_token, ip=ip, user_agent=ua)
    if rotated is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    new_token, user = rotated
    audit(db, agency_id=user.agency_id, user_id=user.id, action="auth.refresh", ip=ip)
    db.commit()
    return _token_response(db, user, refresh=new_token, ip=ip, user_agent=ua)


@router.post("/logout", status_code=204)
def logout(payload: RefreshIn, request: Request, db: DbDep):
    ip, _ = _client_ctx(request)
    revoke_refresh(db, payload.refresh_token)
    audit(db, agency_id=0, user_id=None, action="auth.logout", ip=ip)
    db.commit()
    return None


@router.get("/me", response_model=TokenOut)
def me(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    access_token = credentials.credentials
    try:
        payload = decode_access_token(access_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, int(payload.get("sub", "0")))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    db.refresh(user)
    return TokenOut(
        access_token=access_token,
        refresh_token=None,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_to_out(user),
        agency=AgencyOut.model_validate(user.agency),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbDep, _: OwnerOrAdmin, current_user: CurrentUser):
    users = (
        db.query(User)
        .filter(User.agency_id == current_user.agency_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [user_to_out(u) for u in users]


@router.post("/invite", response_model=InviteOut)
def invite(payload: InviteIn, request: Request, db: DbDep, _: OwnerOrAdmin, current_user: CurrentUser):
    email = payload.email.lower().strip()
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="User already exists")
    temp_password = secrets.token_urlsafe(9)
    user = User(
        agency_id=current_user.agency_id,
        email=email,
        name=payload.name,
        hashed_password=hash_password(temp_password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    ip, _ = _client_ctx(request)
    audit(db, agency_id=current_user.agency_id, user_id=current_user.id, action="user.invite",
          entity_type="user", entity_id=user.id, meta={"email": email, "role": payload.role}, ip=ip)
    db.commit()
    # Send invitation email in background
    try:
        from app.services.email_delivery import send_invite_email
        send_invite_email(email, current_user.agency.name, payload.role, temp_password)
    except Exception:
        logger.warning("Failed to send invite email to %s", email)
    out = user_to_out(user)
    return InviteOut(**out.model_dump(), temp_password=temp_password)


@router.post("/password-reset/request", status_code=200)
def password_reset_request(payload: PasswordResetRequestIn, request: Request, db: DbDep):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    ip, _ = _client_ctx(request)
    # Always behave identically whether or not the user exists (no user enumeration).
    if user is not None:
        token = create_password_reset_token(user.id, user.email)
        audit(db, agency_id=user.agency_id, user_id=user.id, action="auth.password_reset_request", ip=ip)
        db.commit()
        try:
            from app.services.email_delivery import send_password_reset_email
            send_password_reset_email(user.email, token)
        except Exception:
            logger.warning("Failed to send password reset email to %s", user.email)
        return {"detail": "Password reset initiated"}
    db.commit()
    return {"detail": "Password reset initiated"}


@router.post("/password-reset/confirm", status_code=200)
def password_reset_confirm(payload: PasswordResetConfirmIn, request: Request, db: DbDep):
    try:
        data = decode_access_token(payload.token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token") from None
    if data.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token")
    if data.get("email") is None:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    user = db.query(User).filter(User.id == int(data.get("sub", 0))).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    from app.models.refresh_token import RefreshToken

    for rt in db.query(RefreshToken).filter(RefreshToken.user_id == user.id, ~RefreshToken.revoked).all():
        rt.revoked = True
        rt.revoked_at = datetime.now(UTC)
    ip, _ = _client_ctx(request)
    audit(db, agency_id=user.agency_id, user_id=user.id, action="auth.password_reset_confirm", ip=ip)
    db.commit()
    return {"detail": "Password updated. Please log in again."}


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    request: Request,
    db: DbDep,
    _: OwnerOrAdmin,
    current_user: CurrentUser,
):
    target = db.get(User, user_id)
    if target is None or target.agency_id != current_user.agency_id:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("role") and changes["role"] not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}")
    if target.id == current_user.id:
        if changes.get("is_active") is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    for field, value in changes.items():
        setattr(target, field, value)
    ip, _ = _client_ctx(request)
    audit(db, agency_id=current_user.agency_id, user_id=current_user.id, action="user.update",
          entity_type="user", entity_id=target.id, meta=changes, ip=ip)
    db.commit()
    db.refresh(target)
    return user_to_out(target)
