"""User model.

A NexaPilot user is identified by their wallet, not an email/password. One
user may (in later phases) link more than one wallet, so the wallet address
itself lives on the Wallet model — User holds account-level preferences.
"""

from typing import TYPE_CHECKING, List

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RiskLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.policy import Policy
    from app.models.transaction import Transaction
    from app.models.wallet import Wallet


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    display_name: Mapped[str | None] = mapped_column(default=None)

    # The user's own stated risk appetite; the Risk Engine (Phase 4) reads
    # this as one input among several deterministic factors.
    risk_preference: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, native_enum=False, length=16, validate_strings=True),
        default=RiskLevel.MEDIUM,
        server_default=RiskLevel.MEDIUM.value,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    wallets: Mapped[List["Wallet"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    policy: Mapped["Policy"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    activities: Mapped[List["Activity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"<User id={self.id} display_name={self.display_name!r}>"
