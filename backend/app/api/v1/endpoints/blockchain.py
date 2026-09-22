"""
Blockchain layer endpoints.

Flow implemented here (mirrors the project's architecture doc exactly,
minus the AI/Risk/Policy stages which land in Phases 3-4):

    prepare (validate + build unsigned tx)
        -> approve (explicit user-approval step)
        -> submit (client's wallet has signed; we only relay it)
        -> verify (poll the chain, update DB, write an Activity)

The backend never signs a production transaction — /prepare returns an
UNSIGNED tx for the caller's own wallet to sign; /submit only broadcasts an
already-signed raw transaction it's handed.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.blockchain import service
from app.blockchain.client import check_rpc_connection
from app.blockchain.deployment import get_executor_deployment
from app.blockchain.validation import validate_prepare_request
from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.db.base import get_db
from app.models.activity import Activity
from app.models.enums import ActivityType, TransactionStatus
from app.models.policy import Policy
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.blockchain import (
    NetworkStatusResponse,
    PrepareTransactionRequest,
    PreparedTransactionResponse,
    SubmitTransactionRequest,
    UnsignedTransactionOut,
    VerifyTransactionResponse,
    WalletBalanceResponse,
)
from app.schemas.transaction import TransactionRead

logger = logging.getLogger("nexapilot.blockchain")

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


class TransactionStateError(AppError):
    status_code = 409
    code = "INVALID_TRANSACTION_STATE"


def _get_owned_transaction(db: Session, transaction_id: UUID, user: User) -> Transaction:
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user.id)
        .first()
    )
    if tx is None:
        raise NotFoundError("Transaction not found.")
    return tx


@router.get("/network", response_model=NetworkStatusResponse)
def get_network_status() -> NetworkStatusResponse:
    status_info = check_rpc_connection()
    contract_address = None
    try:
        contract_address = get_executor_deployment().address
    except AppError:
        pass  # deployment not found is a valid, reportable state, not a crash

    return NetworkStatusResponse(**status_info, network=settings.blockchain_network, contract_address=contract_address)


@router.get("/wallets/{wallet_id}/balance", response_model=WalletBalanceResponse)
def get_wallet_balance(
    wallet_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletBalanceResponse:
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id, Wallet.user_id == current_user.id).first()
    if wallet is None:
        raise NotFoundError("Wallet not found.")

    native_balance = service.get_native_balance(wallet.address)
    vault_balance = service.get_vault_balance(wallet.address)
    latest_block = service.get_latest_block_number()

    return WalletBalanceResponse(
        address=wallet.address,
        chain=wallet.chain,
        native_balance=native_balance,
        vault_balance=vault_balance,
        as_of_block=latest_block,
    )


@router.post("/transactions/prepare", response_model=PreparedTransactionResponse)
def prepare_transaction(
    payload: PrepareTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreparedTransactionResponse:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.id == payload.wallet_id, Wallet.user_id == current_user.id)
        .first()
    )
    if wallet is None:
        raise NotFoundError("Wallet not found.")

    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")

    # Deterministic, non-AI validation — see app/blockchain/validation.py.
    validate_prepare_request(payload, wallet, policy)

    action_type = payload.action_type or payload.operation.upper()

    raw_unsigned_tx = service.build_unsigned_transaction(
        from_address=wallet.address,
        operation=payload.operation,
        amount=payload.amount,
        target_contract=payload.target_contract,
        calldata=payload.calldata,
        protocol=payload.protocol,
        action_type=action_type,
    )
    serialized = service.serialize_unsigned_tx(raw_unsigned_tx)

    tx_row = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        action_type=action_type,
        protocol=payload.protocol,
        token_in="MON",
        amount_in=payload.amount,
        status=TransactionStatus.AWAITING_APPROVAL,
        chain=wallet.chain,
        target_contract=serialized.get("to"),
        calldata=serialized.get("data"),
        unsigned_tx=serialized,
    )
    db.add(tx_row)
    db.commit()
    db.refresh(tx_row)

    return PreparedTransactionResponse(
        transaction_id=str(tx_row.id),
        unsigned_tx=UnsignedTransactionOut(**serialized),
    )


@router.post("/transactions/{transaction_id}/approve", response_model=TransactionRead)
def approve_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    """Explicit user-approval step — required before /submit will accept a
    signed transaction for this record. This is the project's non-negotiable
    'user remains in control of the wallet' checkpoint made concrete."""
    tx = _get_owned_transaction(db, transaction_id, current_user)
    if tx.status != TransactionStatus.AWAITING_APPROVAL:
        raise TransactionStateError(f"Transaction is '{tx.status.value}', not awaiting approval.")

    tx.status = TransactionStatus.APPROVED
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/transactions/{transaction_id}/submit", response_model=TransactionRead)
def submit_transaction(
    transaction_id: UUID,
    payload: SubmitTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    """Relay an already-signed raw transaction. The backend never signs
    this itself — it only broadcasts what the caller's wallet already
    signed and hands back the resulting tx hash."""
    tx = _get_owned_transaction(db, transaction_id, current_user)
    if tx.status != TransactionStatus.APPROVED:
        raise TransactionStateError(f"Transaction is '{tx.status.value}', not approved for submission.")

    tx_hash = service.send_raw_transaction(payload.signed_raw_tx)

    tx.status = TransactionStatus.SUBMITTED
    tx.tx_hash = tx_hash
    db.commit()
    db.refresh(tx)

    db.add(
        Activity(
            user_id=current_user.id,
            type=ActivityType.TRANSACTION,
            title=f"{tx.action_type} submitted",
            description=f"{tx.amount_in} {tx.token_in} via {tx.protocol} — tx {tx_hash}",
            related_transaction_id=tx.id,
            activity_metadata={"tx_hash": tx_hash, "status": tx.status.value},
        )
    )
    db.commit()

    return tx


@router.post("/transactions/{transaction_id}/verify", response_model=VerifyTransactionResponse)
def verify_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifyTransactionResponse:
    tx = _get_owned_transaction(db, transaction_id, current_user)

    if tx.status not in (TransactionStatus.SUBMITTED, TransactionStatus.CONFIRMED, TransactionStatus.FAILED):
        raise TransactionStateError(f"Transaction is '{tx.status.value}'; nothing to verify yet.")

    if tx.status in (TransactionStatus.CONFIRMED, TransactionStatus.FAILED):
        return VerifyTransactionResponse(
            transaction_id=str(tx.id),
            status=tx.status.value,
            tx_hash=tx.tx_hash,
            block_number=tx.block_number,
            confirmations=None,
            message="Already finalized.",
        )

    receipt = service.get_receipt(tx.tx_hash)
    if receipt is None:
        return VerifyTransactionResponse(
            transaction_id=str(tx.id),
            status=tx.status.value,
            tx_hash=tx.tx_hash,
            message="Not yet mined. Try again shortly.",
        )

    latest_block = service.get_latest_block_number()
    confirmations = max(0, latest_block - receipt["blockNumber"] + 1)
    mined_successfully = receipt["status"] == 1

    tx.status = TransactionStatus.CONFIRMED if mined_successfully else TransactionStatus.FAILED
    tx.block_number = receipt["blockNumber"]
    tx.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tx)

    db.add(
        Activity(
            user_id=current_user.id,
            type=ActivityType.TRANSACTION,
            title=f"{tx.action_type} {'confirmed' if mined_successfully else 'failed'}",
            description=f"{tx.amount_in} {tx.token_in} via {tx.protocol} — block {tx.block_number}",
            related_transaction_id=tx.id,
            activity_metadata={
                "tx_hash": tx.tx_hash,
                "block_number": tx.block_number,
                "confirmations": confirmations,
                "status": tx.status.value,
            },
        )
    )
    db.commit()

    return VerifyTransactionResponse(
        transaction_id=str(tx.id),
        status=tx.status.value,
        tx_hash=tx.tx_hash,
        block_number=tx.block_number,
        confirmations=confirmations,
        message="Confirmed." if mined_successfully else "Transaction reverted on-chain.",
    )
