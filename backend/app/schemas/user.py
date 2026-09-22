from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel
from app.schemas.common import IDTimestampMixin, ORMBase


class UserRead(ORMBase, IDTimestampMixin):
    display_name: Optional[str] = None
    risk_preference: RiskLevel
    is_active: bool


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    risk_preference: Optional[RiskLevel] = None
