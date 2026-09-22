from decimal import Decimal
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

OperationType = Literal["deposit", "withdraw", "execute"]


class PrepareTransactionRequest(BaseModel):
    """Body for POST /api/v1/blockchain/transactions/prepare.

    `operation` maps 1:1 to one of the contract's three entry points
    (deposit/withdraw/execute) — see app/blockchain/validation.py for the
    deterministic checks applied before this is ever turned into a tx.
    """

    wallet_id: str = Field(..., description="UUID of one of the caller's own wallets.")
    operation: OperationType
    amount: Decimal = Field(..., gt=0, description="Amount in whole MON (native units), not wei.")
    protocol: str = Field(default="nexapilot-vault", max_length=64)
    action_type: Optional[str] = Field(default=None, max_length=32)
    target_contract: Optional[str] = Field(default=None, description="Required when operation='execute'.")
    calldata: str = Field(default="0x", description="Raw hex calldata forwarded to target_contract.")

    @field_validator("calldata")
    @classmethod
    def _validate_calldata(cls, value: str) -> str:
        if not value.startswith("0x"):
            raise ValueError("calldata must be a 0x-prefixed hex string.")
        return value


class UnsignedTransactionOut(BaseModel):
    """An unsigned transaction the client's wallet must sign and send back
    via /submit. All numeric fields are hex strings — never raw JSON
    numbers — since wei amounts can exceed JS's safe integer range.

    Fee fields are optional because the backend falls back to a legacy
    gasPrice tx if the chain doesn't expose EIP-1559 fee data — exactly one
    of (max_fee_per_gas + max_priority_fee_per_gas) or gas_price will be set.
    """

    from_address: str = Field(alias="from")
    to: str
    data: str
    value: str
    nonce: str
    chain_id: str = Field(alias="chainId")
    gas: str
    max_fee_per_gas: Optional[str] = Field(default=None, alias="maxFeePerGas")
    max_priority_fee_per_gas: Optional[str] = Field(default=None, alias="maxPriorityFeePerGas")
    gas_price: Optional[str] = Field(default=None, alias="gasPrice")
    type: Optional[str] = None

    model_config = {"populate_by_name": True}


class PreparedTransactionResponse(BaseModel):
    transaction_id: str
    unsigned_tx: UnsignedTransactionOut


class SubmitTransactionRequest(BaseModel):
    signed_raw_tx: str = Field(..., description="0x-prefixed signed raw transaction hex.")

    @field_validator("signed_raw_tx")
    @classmethod
    def _validate_hex(cls, value: str) -> str:
        if not value.startswith("0x"):
            raise ValueError("signed_raw_tx must be a 0x-prefixed hex string.")
        return value


class VerifyTransactionResponse(BaseModel):
    transaction_id: str
    status: str
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    confirmations: Optional[int] = None
    message: str


class WalletBalanceResponse(BaseModel):
    address: str
    chain: str
    native_balance: Decimal = Field(description="Native MON balance held directly in the wallet.")
    vault_balance: Decimal = Field(description="MON balance tracked for this address inside NexaPilotExecutor.")
    as_of_block: Optional[int] = None


class NetworkStatusResponse(BaseModel):
    connected: bool
    chain_id: Optional[int] = None
    expected_chain_id: int
    chain_id_matches: Optional[bool] = None
    latest_block: Optional[int] = None
    rpc_url: str
    network: str
    contract_address: Optional[str] = None
    error: Optional[str] = None
