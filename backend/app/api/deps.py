from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Permission, role_has
from app.core.security import decode_access_token
from app.models.agency import Agency
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[Session, Depends(get_db)]


def _fail() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for this action",
    )


def get_current_user(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None:
        raise _fail()
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _fail() from None
    if payload.get("type") != "access":
        raise _fail()
    user_id = int(payload.get("sub", "0"))
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _fail()
    # Bind tokens to their agency: a token minted for agency B must not access agency A.
    token_agency = payload.get("agency_id")
    if token_agency is not None and int(token_agency) != user.agency_id:
        raise _fail()
    return user


def get_current_agency(
    db: DbDep,
    user: Annotated[User, Depends(get_current_user)],
) -> Agency:
    agency = db.get(Agency, user.agency_id)
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found")
    return agency


def require_permission(permission: str | Permission):
    """Dependency factory enforcing a granular permission on the endpoint."""

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not role_has(user.role, permission):
            raise _forbid()
        return user

    return checker


def require_role(*roles: str):
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise _forbid()
        return user

    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAgency = Annotated[Agency, Depends(get_current_agency)]
OwnerOrAdmin = Annotated[User, Depends(require_role("owner", "admin"))]
