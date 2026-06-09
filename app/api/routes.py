from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_tenant
from app.models.tenant import Tenant

router = APIRouter()


@router.get("/me")
async def get_me(tenant: Tenant = Depends(get_current_tenant)):
    return {"tenant_id": tenant.id, "name": tenant.name}
