from sqlmodel import SQLModel, Field
from typing import Optional
import uuid

class Organization(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    tenant_id: str = Field(foreign_key="tenant.id")