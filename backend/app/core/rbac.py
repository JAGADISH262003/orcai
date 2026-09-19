"""Role-based access control: roles -> granular permissions."""

from enum import StrEnum


class Permission(StrEnum):
    CONTRACTS_READ = "contracts.read"
    CONTRACTS_WRITE = "contracts.write"
    SEEKERS_READ = "seekers.read"
    SEEKERS_WRITE = "seekers.write"
    MATCHES_READ = "matches.read"
    MATCHES_WRITE = "matches.write"
    HITL_READ = "hitl.read"
    HITL_REVIEW = "hitl.review"
    BILLING_READ = "billing.read"
    BILLING_WRITE = "billing.write"
    TEAMS_MANAGE = "teams.manage"
    AUDIT_READ = "audit.read"
    SETTINGS_WRITE = "settings.write"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "owner": set(Permission),
    "admin": set(Permission) - {Permission.BILLING_WRITE},
    "recruiter": {
        Permission.CONTRACTS_READ,
        Permission.CONTRACTS_WRITE,
        Permission.SEEKERS_READ,
        Permission.SEEKERS_WRITE,
        Permission.MATCHES_READ,
        Permission.MATCHES_WRITE,
        Permission.HITL_READ,
        Permission.HITL_REVIEW,
    },
    "client": {
        Permission.CONTRACTS_READ,
        Permission.MATCHES_READ,
    },
}

VALID_ROLES = set(ROLE_PERMISSIONS)


def role_has(role: str, permission: str | Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
