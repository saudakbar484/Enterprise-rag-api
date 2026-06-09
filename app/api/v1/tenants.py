import uuid

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_tenant
from app.core.database import get_session
from app.models.tenant import Tenant

router = APIRouter()


def hash_api_key(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_api_key(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: str
    name: str
    api_key: str


class TenantPublic(BaseModel):
    id: str
    name: str


ADMIN_SECRET = "super-secret-admin-token"


async def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    body: TenantCreate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(verify_admin),
):
    raw_api_key = str(uuid.uuid4())
    hashed_api_key = hash_api_key(raw_api_key)

    tenant = Tenant(id=str(uuid.uuid4()), name=body.name, api_key=hashed_api_key)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(id=tenant.id, name=tenant.name, api_key=raw_api_key)


@router.get("/me", response_model=TenantPublic)
async def get_me(tenant: Tenant = Depends(get_current_tenant)):
    return TenantPublic(id=tenant.id, name=tenant.name)
