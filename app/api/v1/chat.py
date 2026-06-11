import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dependencies import get_current_tenant
from app.services.search import search_tenant_vectors
from app.services.llm import query_llm
from app.models.tenant import Tenant
from app.core.logging import logger
import asyncio

router = APIRouter()


# ── Request / Response schemas ──
class ChatRequest(BaseModel):
    query: str
    limit: int = 5


class SourceReference(BaseModel):
    filename: str
    chunk_index: int
    score: float


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceReference]
    tenant_id: str
    retrieval_ms: float
    llm_ms: float
    total_ms: float


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    total_start = time.perf_counter()

    # Step 1 — retrieve relevant chunks from Qdrant
    retrieval_start = time.perf_counter()
    results = await asyncio.to_thread(
        search_tenant_vectors,
        query=body.query,
        tenant_id=tenant.id,
        limit=body.limit,
    )
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

    logger.info("chat_retrieval", extra={
        "tenant_id": tenant.id,
        "query": body.query[:50],
        "results_count": len(results),
        "retrieval_ms": round(retrieval_ms, 2),
    })

    # Step 2 — build snippets for LLM
    snippets = [
        {
            "filename": r.filename,
            "chunk_index": r.chunk_index,
            "text": r.text,
        }
        for r in results
    ]

    # Step 3 — query LLM asynchronously
    llm_start = time.perf_counter()
    answer = await asyncio.to_thread(
        query_llm,
        query=body.query,
        snippets=snippets,
    )
    llm_ms = (time.perf_counter() - llm_start) * 1000

    total_ms = (time.perf_counter() - total_start) * 1000

    logger.info("chat_complete", extra={
        "tenant_id": tenant.id,
        "retrieval_ms": round(retrieval_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "total_ms": round(total_ms, 2),
    })

    # Step 4 — build structured response
    sources = [
        SourceReference(
            filename=r.filename,
            chunk_index=r.chunk_index,
            score=round(r.score, 4),
        )
        for r in results
    ]

    return ChatResponse(
        query=body.query,
        answer=answer,
        sources=sources,
        tenant_id=tenant.id,
        retrieval_ms=round(retrieval_ms, 2),
        llm_ms=round(llm_ms, 2),
        total_ms=round(total_ms, 2),
    )