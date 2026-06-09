import uuid
from typing import Optional

from sqlmodel import Field, SQLModel


class Organization(SQLModel, table=True):
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True
    )
    name: str
    tenant_id: str = Field(foreign_key="tenant.id")
