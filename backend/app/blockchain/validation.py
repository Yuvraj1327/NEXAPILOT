"""
Secure, deterministic transaction validation — Phase 2 baseline.

This is deliberately NOT the Risk Engine or the Policy Engine (both land in
Phase 4). It's the minimal, non-AI, non-bypassable set of checks the project
rules require before *anything* is ever turned into an on-chain call:
amount sanity, the user's already-stored spending ceiling (from their
Policy row — see Phase 1), and on-chain target allow-listing. Phase 4 will
compose additional checks (daily limits, allowed-protocol matching, max
risk level, approval requirements) on top of this, not replace it.
"""

from decimal import Decimal

from web3 import Web3

from app.blockchain.client import get_executor_contract
from app.core.exceptions import AppError
from app.models.policy import Policy
from app.models.wallet import Wallet
from app.schemas.blockchain import PrepareTransactionRequest

SUPPORTED_CHAIN = "monad"


class TransactionValidationError(AppError):
    status_code = 400
    code = "TRANSACTION_REJECTED"


def validate_prepare_request(request: PrepareTransactionRequest, wallet: Wallet, policy: Policy) -> None:
    """Raise TransactionValidationError if the request fails any
    deterministic, non-AI-influenced check. Returns None (no exception) if
    it passes every check.
    """
    if wallet.chain != SUPPORTED_CHAIN:
        raise TransactionValidationError(f"Unsupported chain '{wallet.chain}'. Only '{SUPPORTED_CHAIN}' is supported.")

    if request.amount <= 0:
        raise TransactionValidationError("Amount must be greater than zero.")

    # Baseline ceiling check against the user's own stored Policy limit.
    # NOTE: this is a flat threshold check only. Daily limits, allowed
    # protocol/action matching, and risk-level gating are Phase 4 work.
    if request.amount > policy.max_transaction_amount:
        raise TransactionValidationError(
            f"Amount {request.amount} MON exceeds your policy's max transaction amount "
            f"of {policy.max_transaction_amount} MON."
        )

    if request.operation == "execute":
        if not request.target_contract:
            raise TransactionValidationError("target_contract is required for an 'execute' operation.")
        if not Web3.is_address(request.target_contract):
            raise TransactionValidationError(f"'{request.target_contract}' is not a valid address.")
        if not request.action_type:
            raise TransactionValidationError("action_type is required for an 'execute' operation.")
        if not request.protocol:
            raise TransactionValidationError("protocol is required for an 'execute' operation.")

        # Defense-in-depth check against the SAME on-chain allow-list the
        # contract itself enforces — fail fast with a friendly error rather
        # than making the user sign a transaction that will revert.
        contract = get_executor_contract()
        target = Web3.to_checksum_address(request.target_contract)
        is_allowed = contract.functions.allowedTargets(target).call()
        if not is_allowed:
            raise TransactionValidationError(
                f"Target contract {target} is not on the allow-list for this deployment."
            )


def to_wei(amount: Decimal) -> int:
    return Web3.to_wei(amount, "ether")


def from_wei(amount_wei: int) -> Decimal:
    return Decimal(Web3.from_wei(amount_wei, "ether"))
