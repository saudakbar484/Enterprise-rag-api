from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.dependencies import get_current_tenant
from app.services.search import search_tenant_vectors
from app.models.tenant import Tenant

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class SearchResultResponse(BaseModel):
    chunk_index: int
    text: str
    score: float
    filename: str


@router.post("/")
async def search_documents(
    body: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
) -> list[SearchResultResponse]:
    results = search_tenant_vectors(
        query=body.query,
        tenant_id=tenant.id,
        limit=body.limit,
    )

    return [
        SearchResultResponse(
            chunk_index=r.chunk_index,
            text=r.text,
            score=r.score,
            filename=r.filename,
        )
        for r in results
    ]