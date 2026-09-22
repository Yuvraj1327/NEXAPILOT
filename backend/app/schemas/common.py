"""Shared schema building blocks."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base for response schemas built from SQLAlchemy ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class IDTimestampMixin(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
