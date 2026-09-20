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
    INTERVIEWS_READ = "interviews.read"
    INTERVIEWS_WRITE = "interviews.write"
    NOTES_READ = "notes.read"
    NOTES_WRITE = "notes.write"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_WRITE = "documents.write"
    CAMPAIGNS_READ = "campaigns.read"
    CAMPAIGNS_WRITE = "campaigns.write"
    SCORECARDS_READ = "scorecards.read"
    SCORECARDS_WRITE = "scorecards.write"
    WEBHOOKS_READ = "webhooks.read"
    WEBHOOKS_WRITE = "webhooks.write"
    EMAIL_SEND = "email.send"
    NOTIFICATIONS_READ = "notifications.read"
    TAGS_READ = "tags.read"
    TAGS_WRITE = "tags.write"
    ACTIVITY_READ = "activity.read"
    ANALYTICS_READ = "analytics.read"
    OFFERS_READ = "offers.read"
    OFFERS_WRITE = "offers.write"


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
        Permission.INTERVIEWS_READ,
        Permission.INTERVIEWS_WRITE,
        Permission.NOTES_READ,
        Permission.NOTES_WRITE,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.CAMPAIGNS_READ,
        Permission.CAMPAIGNS_WRITE,
        Permission.SCORECARDS_READ,
        Permission.SCORECARDS_WRITE,
        Permission.EMAIL_SEND,
        Permission.NOTIFICATIONS_READ,
        Permission.TAGS_READ,
        Permission.TAGS_WRITE,
        Permission.ACTIVITY_READ,
        Permission.ANALYTICS_READ,
        Permission.OFFERS_READ,
        Permission.OFFERS_WRITE,
    },
    "client": {
        Permission.CONTRACTS_READ,
        Permission.MATCHES_READ,
        Permission.NOTIFICATIONS_READ,
        Permission.ANALYTICS_READ,
    },
}

VALID_ROLES = set(ROLE_PERMISSIONS)


def role_has(role: str, permission: str | Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
