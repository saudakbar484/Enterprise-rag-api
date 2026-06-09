from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.models.tenant import Tenant

async def get_current_tenant(
    x_tenant_api_key: str = Header(...),
    session: AsyncSession = Depends(get_session)
) -> Tenant:
    result = await session.execute(
        select(Tenant).where(Tenant.api_key == x_tenant_api_key)
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    return tenant