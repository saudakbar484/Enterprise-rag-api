from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class Tenant(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    api_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)