from web3 import Web3
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import IDTimestampMixin, ORMBase


class WalletRead(ORMBase, IDTimestampMixin):
    address: str
    chain: str
    is_primary: bool


class WalletConnectRequest(BaseModel):
    """Body for POST /api/v1/auth/connect."""

    address: str = Field(..., min_length=4, max_length=64, examples=["0xAbC123..."])
    chain: str = Field(default="monad", max_length=32)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str) -> str:
        value = value.strip()
        # Monad is EVM-compatible, so a wallet address must be a well-formed
        # 20-byte hex address — catch a malformed one here, at the door,
        # rather than as a confusing failure deep in a later web3 call.
        if not Web3.is_address(value):
            raise ValueError(f"'{value}' is not a valid EVM address.")
        return value.lower()
