"""Policy model.

Schema only in Phase 1 — the Policy Engine (Phase 4) is what actually
*evaluates* these rules against a proposed action. This table just gives
each user a durable, editable record of the limits they've set.

MVP keeps one active policy row per user (enforced via unique constraint).
"""

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import JSON, ForeignKey, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RiskLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Numeric(precision, scale) — stored as a fixed-point decimal, never a
    # float, since this gates real on-chain transaction amounts.
    max_transaction_amount: Mapped[float] = mapped_column(Numeric(30, 10), nullable=False)
    daily_limit: Mapped[float] = mapped_column(Numeric(30, 10), nullable=False)

    # Lists of protocol/action identifiers this user's AI actions may touch.
    # JSON is portable (works identically on SQLite for local dev/tests and
    # Postgres/Supabase in every real environment).
    allowed_protocols: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_actions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    max_risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, native_enum=False, length=16, validate_strings=True),
        default=RiskLevel.MEDIUM,
        server_default=RiskLevel.MEDIUM.value,
        nullable=False,
    )
    approval_required: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    user: Mapped["User"] = relationship(back_populates="policy")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Policy user_id={self.user_id} max_tx={self.max_transaction_amount}>"
