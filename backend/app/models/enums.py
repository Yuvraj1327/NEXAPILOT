"""
Shared enums used across ORM models and Pydantic schemas.

Kept as plain Python `str` enums (not native Postgres enum types) so adding
a new value later is a normal column CHECK-constraint migration rather than
an out-of-transaction ALTER TYPE — this schema will evolve through Phases
3-4 (Risk Engine, Policy Engine) and we want that to stay cheap.
"""

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"  # AI proposed it; not yet risk/policy checked
    RISK_REJECTED = "RISK_REJECTED"
    POLICY_REJECTED = "POLICY_REJECTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED_BY_USER = "REJECTED_BY_USER"
    SUBMITTED = "SUBMITTED"  # sent to the Monad network
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class ActivityType(str, Enum):
    TRANSACTION = "TRANSACTION"
    PORTFOLIO_UPDATE = "PORTFOLIO_UPDATE"
    RECOMMENDATION = "RECOMMENDATION"
    SYSTEM = "SYSTEM"
