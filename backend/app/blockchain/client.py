"""Web3 client + contract handle, built once and reused."""

import logging
from functools import lru_cache

from web3 import Web3
from web3.contract import Contract

from app.blockchain.deployment import get_executor_deployment
from app.core.config import settings

logger = logging.getLogger("nexapilot.blockchain")


@lru_cache
def get_web3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(settings.monad_rpc_url, request_kwargs={"timeout": 10}))
    return w3


def check_rpc_connection() -> dict:
    """Best-effort RPC health probe. Never raises — used by health/status
    endpoints that should degrade gracefully instead of 500ing."""
    w3 = get_web3()
    try:
        connected = w3.is_connected()
        chain_id = w3.eth.chain_id if connected else None
        block_number = w3.eth.block_number if connected else None
        return {
            "connected": bool(connected),
            "chain_id": chain_id,
            "expected_chain_id": settings.monad_chain_id,
            "chain_id_matches": chain_id == settings.monad_chain_id if chain_id is not None else None,
            "latest_block": block_number,
            "rpc_url": settings.monad_rpc_url,
        }
    except Exception as exc:  # noqa: BLE001 — deliberately broad for a health probe
        logger.warning("Monad RPC connectivity check failed: %s", exc)
        return {
            "connected": False,
            "chain_id": None,
            "expected_chain_id": settings.monad_chain_id,
            "chain_id_matches": None,
            "latest_block": None,
            "rpc_url": settings.monad_rpc_url,
            "error": str(exc),
        }


@lru_cache
def get_executor_contract() -> Contract:
    w3 = get_web3()
    deployment = get_executor_deployment()
    return w3.eth.contract(address=Web3.to_checksum_address(deployment.address), abi=deployment.abi)
