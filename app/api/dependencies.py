import bcrypt
from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.models.tenant import Tenant

async def get_current_tenant(
    x_tenant_api_key: str = Header(...),
    session: AsyncSession = Depends(get_session)
) -> Tenant:
    result = await session.execute(select(Tenant))
    tenants = result.scalars().all()

    for tenant in tenants:
        try:
            if bcrypt.checkpw(x_tenant_api_key.encode(), tenant.api_key.encode()):
                return tenant
        except Exception:
            continue

    raise HTTPException(status_code=403, detail="Invalid or missing API key")