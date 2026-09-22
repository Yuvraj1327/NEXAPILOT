"""
Import every model module here so that:

1. `Base.metadata` is fully populated for Alembic autogenerate and any
   `Base.metadata.create_all(...)` calls (tests).
2. Relationship string references (e.g. Mapped["Wallet"]) resolve correctly
   regardless of which module is imported first.
"""

from app.models.activity import Activity  # noqa: F401
from app.models.policy import Policy  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.wallet import Wallet  # noqa: F401

__all__ = ["User", "Wallet", "Policy", "Transaction", "Activity"]
