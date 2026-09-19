from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.config import get_settings
from app.core.rbac import ROLE_PERMISSIONS
from app.core.workflows import DEFAULT_WORKFLOW, workflow_by_type
from app.models.user import User

settings = get_settings()


class AgencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    tier: str
    workflow_type: str = DEFAULT_WORKFLOW
    workflow: dict
    description: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def fill_workflow(cls, v):
        if hasattr(v, "workflow_type") and hasattr(v, "ensure_workflow_config"):
            v.ensure_workflow_config()
            blueprint = workflow_by_type(v.workflow_type)
            return {**v.__dict__, "workflow": blueprint}
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: str
    phone: str | None = None
    is_active: bool
    permissions: list[str] = []
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 0
    user: UserOut
    agency: AgencyOut


class RegisterIn(BaseModel):
    agency_name: str = Field(min_length=2, max_length=160)
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    workflow_type: str | None = Field(default=None, max_length=40)

    @property
    def workflow(self) -> str:
        return self.workflow_type or DEFAULT_WORKFLOW


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class UserUpdateIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None


class InviteIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=160)
    role: str = "recruiter"


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class InviteOut(UserOut):
    temp_password: str


def user_to_out(user: User) -> UserOut:
    permissions = sorted(p.value for p in ROLE_PERMISSIONS.get(user.role, set()))
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        phone=user.phone,
        is_active=user.is_active,
        permissions=permissions,
        created_at=user.created_at,
    )
