"""Wallet model.

Stores the on-chain address(es) linked to a user. The MVP uses exactly one
wallet per user (created alongside the user on first connect), but the
table is modeled to support multiple wallets/chains without a schema
change later.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Wallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("chain", "address", name="uq_wallets_chain_address"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Stored lowercase/checksum-normalized by the API layer, never trust
    # client casing for uniqueness.
    address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(32), default="monad", server_default="monad", nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    user: Mapped["User"] = relationship(back_populates="wallets")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Wallet id={self.id} chain={self.chain} address={self.address}>"
