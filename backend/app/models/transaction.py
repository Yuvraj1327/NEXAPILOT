"""Transaction model.

Represents one proposed-then-executed on-chain action, all the way from the
AI's structured proposal through risk/policy evaluation, user approval, and
on-chain confirmation. Phase 1 only defines the shape of this record; the
Risk Engine, Policy Engine, and execution pipeline (Phases 3-6) are the ones
that populate and transition it.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RiskLevel, TransactionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wallet import Wallet


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # e.g. "SWAP", "STAKE", "LEND", "WITHDRAW" — kept as a free string in
    # Phase 1 rather than an enum since the supported action set is defined
    # by the Claude structured-action schema landing in Phase 3.
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    protocol: Mapped[str] = mapped_column(String(64), nullable=False)

    token_in: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_in: Mapped[float] = mapped_column(Numeric(30, 10), nullable=False)
    token_out: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    amount_out: Mapped[Optional[float]] = mapped_column(Numeric(30, 10), default=None)

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, native_enum=False, length=32, validate_strings=True),
        default=TransactionStatus.PENDING,
        server_default=TransactionStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    risk_level: Mapped[Optional[RiskLevel]] = mapped_column(
        SAEnum(RiskLevel, native_enum=False, length=16, validate_strings=True),
        default=None,
    )
    # Free-form audit trail of *why* risk/policy engines decided what they
    # decided — kept as JSON so those phases can shape it without a migration.
    risk_explanation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=None)
    policy_decision: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=None)

    # The raw structured action Claude proposed, stored verbatim for audit —
    # this is untrusted input, never executed directly (see project rules).
    raw_ai_action: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=None)

    chain: Mapped[str] = mapped_column(String(32), default="monad", server_default="monad", nullable=False)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), default=None, index=True)

    # --- Blockchain layer (Phase 2) ---
    # Populated only for operation="execute" — the on-chain protocol/target
    # this action forwards value+calldata to.
    target_contract: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    calldata: Mapped[Optional[str]] = mapped_column(String, default=None)
    # The exact unsigned transaction returned to the client for signing —
    # kept for audit/debugging; never contains a signature or private key.
    unsigned_tx: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=None)
    block_number: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped["User"] = relationship(back_populates="transactions")
    wallet: Mapped["Wallet"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction id={self.id} status={self.status} protocol={self.protocol}>"
