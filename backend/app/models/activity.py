"""Activity model.

A user-facing timeline/audit log: transaction lifecycle events, portfolio
snapshots, AI recommendations shown, and system notices. Populated by later
phases; Phase 1 only defines the table.
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ActivityType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[ActivityType] = mapped_column(
        SAEnum(ActivityType, native_enum=False, length=32, validate_strings=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), default=None)

    related_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), default=None, index=True
    )
    # Arbitrary structured payload for the specific activity type (e.g. a
    # portfolio snapshot, or the fields of a recommendation).
    activity_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=None)

    user: Mapped["User"] = relationship(back_populates="activities")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Activity id={self.id} type={self.type} title={self.title!r}>"
