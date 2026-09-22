"""
Blockchain service layer: wallet balances, contract interaction,
unsigned-transaction construction, and on-chain verification.

Design boundary that matters for the project's "AI must not control the
wallet" / "never expose private keys" rules: everything in this module
either (a) only *reads* chain state, or (b) *builds an unsigned
transaction* for a wallet to sign itself. Nothing here signs a production
transaction on a user's behalf — see scripts/dev_sign_and_send.py for the
Phase 2 integration-test-only signer, which is explicitly not part of the
API surface.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from web3 import Web3
from web3.exceptions import TimeExhausted, TransactionNotFound

from app.blockchain.client import get_executor_contract, get_web3
from app.blockchain.validation import from_wei, to_wei
from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger("nexapilot.blockchain")


class RpcUnavailableError(AppError):
    status_code = 503
    code = "BLOCKCHAIN_RPC_UNAVAILABLE"


class TransactionBroadcastError(AppError):
    status_code = 502
    code = "TRANSACTION_BROADCAST_FAILED"


def _wrap_rpc_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Monad RPC call failed: %s", exc)
        raise RpcUnavailableError(f"Could not reach the Monad RPC endpoint: {exc}") from exc


# --- reads ---


def get_native_balance(address: str) -> Decimal:
    w3 = get_web3()
    balance_wei = _wrap_rpc_call(w3.eth.get_balance, Web3.to_checksum_address(address))
    return from_wei(balance_wei)


def best_effort_native_balance(address: str) -> Optional[Decimal]:
    """Same as get_native_balance, but never raises — used by the Phase 4
    Risk Engine's amount-concentration factor, which has a documented
    fallback for when a live balance just isn't available (RPC down,
    address unreachable) and shouldn't turn into a hard failure for an
    otherwise-successful AI query or risk assessment."""
    try:
        return get_native_balance(address)
    except AppError as exc:
        logger.warning("Could not fetch wallet balance (best-effort): %s", exc)
        return None


def get_vault_balance(address: str) -> Decimal:
    contract = get_executor_contract()
    balance_wei = _wrap_rpc_call(contract.functions.balanceOf(Web3.to_checksum_address(address)).call)
    return from_wei(balance_wei)


def get_latest_block_number() -> int:
    w3 = get_web3()
    return _wrap_rpc_call(lambda: w3.eth.block_number)


# --- unsigned transaction construction ---


def _estimate_fees(w3: Web3) -> Dict[str, int]:
    """EIP-1559 fee estimation with a safe fallback for chains/clients that
    don't expose eth_maxPriorityFeePerGas."""
    try:
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is None:
            gas_price = w3.eth.gas_price
            return {"gasPrice": gas_price, "type": 0}

        try:
            priority_fee = w3.eth.max_priority_fee
        except Exception:  # noqa: BLE001
            priority_fee = Web3.to_wei(1, "gwei")

        max_fee = base_fee * 2 + priority_fee
        return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": priority_fee, "type": 2}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fee estimation fell back to a fixed gas price: %s", exc)
        return {"gasPrice": Web3.to_wei(2, "gwei"), "type": 0}


def build_unsigned_transaction(
    *,
    from_address: str,
    operation: str,
    amount: Decimal,
    target_contract: Optional[str] = None,
    calldata: str = "0x",
    protocol: str = "",
    action_type: str = "",
) -> Dict[str, Any]:
    """Build an unsigned transaction dict (all-int values, web3-native
    shape) for one of the contract's three operations. The caller's own
    wallet is the only thing that ever signs this."""
    w3 = get_web3()
    contract = get_executor_contract()
    from_checksum = Web3.to_checksum_address(from_address)
    amount_wei = to_wei(amount)

    if operation == "deposit":
        fn = contract.functions.deposit()
        base_tx: Dict[str, Any] = {"from": from_checksum, "value": amount_wei}
    elif operation == "withdraw":
        fn = contract.functions.withdraw(amount_wei)
        base_tx = {"from": from_checksum, "value": 0}
    elif operation == "execute":
        if not target_contract:
            raise AppError("target_contract is required for an 'execute' operation.")
        fn = contract.functions.execute(
            Web3.to_checksum_address(target_contract),
            amount_wei,
            bytes.fromhex(calldata[2:]) if calldata.startswith("0x") else bytes.fromhex(calldata),
            protocol,
            action_type,
        )
        base_tx = {"from": from_checksum, "value": 0}
    else:
        raise AppError(f"Unknown operation '{operation}'.")

    base_tx["nonce"] = _wrap_rpc_call(w3.eth.get_transaction_count, from_checksum, "pending")
    base_tx["chainId"] = settings.monad_chain_id
    base_tx.update(_estimate_fees(w3))

    try:
        gas_estimate = fn.estimate_gas(base_tx)
    except Exception as exc:  # noqa: BLE001
        # A revert here means the call would fail on-chain too — surface it
        # as a validation-style error rather than a generic RPC failure.
        logger.info("Gas estimation reverted for operation=%s: %s", operation, exc)
        raise AppError(f"Transaction would fail on-chain: {exc}", details={"operation": operation}) from exc

    # Headroom on the estimate — cheap insurance against out-of-gas on a
    # slightly different chain state by the time the user actually signs.
    base_tx["gas"] = int(gas_estimate * 1.2)

    unsigned_tx = fn.build_transaction(base_tx)
    return unsigned_tx


def serialize_unsigned_tx(tx: Dict[str, Any]) -> Dict[str, str]:
    """Hex-encode every field so large wei/gas values survive JSON without
    precision loss on JS clients."""

    def to_hex(value: Any) -> str:
        if isinstance(value, bytes):
            return "0x" + value.hex()
        if isinstance(value, int):
            return hex(value)
        return value

    return {key: to_hex(value) for key, value in tx.items()}


# --- broadcast + verification ---


def send_raw_transaction(signed_raw_tx: str) -> str:
    w3 = get_web3()
    try:
        tx_hash = w3.eth.send_raw_transaction(bytes.fromhex(signed_raw_tx[2:]))
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Broadcasting signed transaction failed: %s", exc)
        raise TransactionBroadcastError(f"Failed to broadcast transaction: {exc}") from exc

    hash_hex = tx_hash.hex()
    return hash_hex if hash_hex.startswith("0x") else f"0x{hash_hex}"


def get_receipt(tx_hash: str) -> Optional[Dict[str, Any]]:
    """Returns the receipt dict if mined, else None (never raises for the
    'not mined yet' case — that's an expected, normal state)."""
    w3 = get_web3()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        return dict(receipt)
    except TransactionNotFound:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Fetching receipt for %s failed: %s", tx_hash, exc)
        raise RpcUnavailableError(f"Could not fetch transaction receipt: {exc}") from exc


def wait_for_receipt(tx_hash: str, timeout_seconds: int) -> Optional[Dict[str, Any]]:
    """Blocks up to `timeout_seconds` for a receipt; returns None on
    timeout rather than raising, since 'still pending' is a normal, valid
    outcome the caller should handle gracefully."""
    w3 = get_web3()
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout_seconds, poll_latency=0.5)
        return dict(receipt)
    except TimeExhausted:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Waiting for receipt for %s failed: %s", tx_hash, exc)
        raise RpcUnavailableError(f"Could not fetch transaction receipt: {exc}") from exc
