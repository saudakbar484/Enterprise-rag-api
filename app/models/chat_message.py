from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True
    )
    tenant_id: str = Field(index=True)
    session_id: str = Field(index=True)
    role: str
    content: str
    token_count: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )