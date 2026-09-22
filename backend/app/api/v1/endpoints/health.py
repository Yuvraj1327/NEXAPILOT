"""Health check — verifies the process is up and its dependencies (DB,
Monad RPC) are reachable. Never raises: a dependency being down is a
'degraded' health report, not a 500."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.blockchain.client import check_rpc_connection
from app.core.config import settings
from app.db.base import get_db

logger = logging.getLogger("nexapilot.health")

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    db_status = "unknown"
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check: database unreachable: %s", exc)
        db_status = "unreachable"

    blockchain_info = check_rpc_connection()
    blockchain_status = "ok" if blockchain_info.get("connected") else "unreachable"
    if blockchain_status != "ok":
        logger.warning("Health check: Monad RPC unreachable: %s", blockchain_info.get("error"))

    overall_ok = db_status == "ok" and blockchain_status == "ok"

    return {
        "status": "ok" if overall_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": db_status,
        "blockchain": {
            "status": blockchain_status,
            "network": settings.blockchain_network,
            "chain_id": blockchain_info.get("chain_id"),
        },
    }
