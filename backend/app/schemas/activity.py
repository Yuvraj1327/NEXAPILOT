from typing import Any, Dict, Optional
from uuid import UUID

from app.models.enums import ActivityType
from app.schemas.common import IDTimestampMixin, ORMBase


class ActivityRead(ORMBase, IDTimestampMixin):
    type: ActivityType
    title: str
    description: Optional[str] = None
    related_transaction_id: Optional[UUID] = None
    activity_metadata: Optional[Dict[str, Any]] = None
