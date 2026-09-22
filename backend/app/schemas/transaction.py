from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from app.models.enums import RiskLevel, TransactionStatus
from app.schemas.common import IDTimestampMixin, ORMBase


class TransactionRead(ORMBase, IDTimestampMixin):
    wallet_id: UUID
    action_type: str
    protocol: str
    token_in: str
    amount_in: Decimal
    token_out: Optional[str] = None
    amount_out: Optional[Decimal] = None
    status: TransactionStatus
    risk_level: Optional[RiskLevel] = None
    risk_explanation: Optional[Dict[str, Any]] = None
    policy_decision: Optional[Dict[str, Any]] = None
    chain: str
    tx_hash: Optional[str] = None
    target_contract: Optional[str] = None
    calldata: Optional[str] = None
    block_number: Optional[int] = None
    confirmed_at: Optional[datetime] = None
