from app.schemas.common import ORMBase
from app.schemas.user import UserRead
from app.schemas.wallet import WalletRead


class TokenResponse(ORMBase):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    wallet: WalletRead
