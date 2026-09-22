from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletRead

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("", response_model=List[WalletRead])
def list_my_wallets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Wallet]:
    return db.query(Wallet).filter(Wallet.user_id == current_user.id).all()
