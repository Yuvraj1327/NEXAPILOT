"""
Wallet-connect auth.

Scope for Phase 1: given a wallet address the frontend already trusts (in
later phases, Privy will have verified the user actually controls it via a
signed message / SIWE flow), get-or-create the corresponding User + Wallet
rows and issue a session JWT.

TODO (frontend/wallet-integration phase): require and verify a wallet
signature here before trusting `address`. Until then, this endpoint must
not be treated as proving wallet ownership — it only establishes a backend
session for an address the frontend claims is connected.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import get_db
from app.models.policy import Policy
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import TokenResponse
from app.schemas.wallet import WalletConnectRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/connect", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def connect_wallet(payload: WalletConnectRequest, db: Session = Depends(get_db)) -> TokenResponse:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.chain == payload.chain, Wallet.address == payload.address)
        .first()
    )

    if wallet is not None:
        user = wallet.user
    else:
        user = User()
        db.add(user)
        db.flush()  # assign user.id without committing yet

        wallet = Wallet(user_id=user.id, address=payload.address, chain=payload.chain, is_primary=True)
        db.add(wallet)

        # Every new user gets a conservative default policy so the Policy
        # Engine (Phase 4) always has something to evaluate against.
        policy = Policy(
            user_id=user.id,
            max_transaction_amount=settings.default_max_transaction_amount,
            daily_limit=settings.default_daily_limit,
            allowed_protocols=[],
            allowed_actions=[],
        )
        db.add(policy)

        db.commit()
        db.refresh(user)
        db.refresh(wallet)

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token, user=user, wallet=wallet)
