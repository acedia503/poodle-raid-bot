from enum import Enum


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    WAITING = "waiting"
    ASSIGNED = "assigned"
    EXCLUDED = "excluded"


class SourceType(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SessionStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    RESET = "reset"


class WaitingStatus(str, Enum):
    WAITING = "waiting"
    EXCLUDED = "excluded"


class BalanceMode(str, Enum):
    MIXED = "mixed"
    POWER_BALANCE = "power_balance"
    STRICT_ROLE = "strict_role"
