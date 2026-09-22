"""
Read-only scaffolding for Phase 1.

Transactions are created by the Claude → Risk Engine → Policy Engine →
execution pipeline built in later phases, not through a generic POST here
— that would let a client (or a compromised AI response) write straight to
this table, bypassing every deterministic check the project rules require.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.base import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionRead])
def list_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_my_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if transaction is None:
        raise NotFoundError("Transaction not found.")
    return transaction
