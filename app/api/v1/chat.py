import time
import json
import asyncio
import concurrent.futures
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dependencies import get_current_tenant
from app.services.search import search_tenant_vectors
from app.services.llm import query_llm, stream_llm
from app.services.history import get_recent_history, build_history_block, save_message
from app.models.tenant import Tenant
from app.core.logging import logger

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    limit: int = 5


class StreamRequest(BaseModel):
    query: str
    session_id: str = "default"
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
    session_id: str
    retrieval_ms: float
    llm_ms: float
    total_ms: float


async def async_generator(fn, *args) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    gen = fn(*args)
    while True:
        try:
            token = await loop.run_in_executor(executor, next, gen)
            yield token
        except StopIteration:
            break


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    total_start = time.perf_counter()

    # Step 1 — retrieve vectors
    retrieval_start = time.perf_counter()
    results = await asyncio.to_thread(
        search_tenant_vectors,
        query=body.query,
        tenant_id=tenant.id,
        limit=body.limit,
    )
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

    snippets = [
        {"filename": r.filename, "chunk_index": r.chunk_index, "text": r.text}
        for r in results
    ]

    # Step 2 — fetch and build history
    history_messages = await get_recent_history(
        session=session,
        tenant_id=tenant.id,
        session_id=body.session_id,
    )
    history_block = build_history_block(history_messages)

    # Step 3 — query LLM with history
    llm_start = time.perf_counter()
    answer = await asyncio.to_thread(
        query_llm,
        query=body.query,
        snippets=snippets,
        history_block=history_block,
    )
    llm_ms = (time.perf_counter() - llm_start) * 1000
    total_ms = (time.perf_counter() - total_start) * 1000

    # Step 4 — save both turns to DB
    await save_message(session, tenant.id, body.session_id, "user", body.query)
    await save_message(session, tenant.id, body.session_id, "assistant", answer)

    logger.info("chat_complete", extra={
        "tenant_id": tenant.id,
        "session_id": body.session_id,
        "history_turns": len(history_messages),
        "retrieval_ms": round(retrieval_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "total_ms": round(total_ms, 2),
    })

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
        session_id=body.session_id,
        retrieval_ms=round(retrieval_ms, 2),
        llm_ms=round(llm_ms, 2),
        total_ms=round(total_ms, 2),
    )


@router.post("/stream")
async def chat_stream(
    body: StreamRequest,
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    results = await asyncio.to_thread(
        search_tenant_vectors,
        query=body.query,
        tenant_id=tenant.id,
        limit=body.limit,
    )

    snippets = [
        {"filename": r.filename, "chunk_index": r.chunk_index, "text": r.text}
        for r in results
    ]

    sources = [
        {"filename": r.filename, "chunk_index": r.chunk_index, "score": round(r.score, 4)}
        for r in results
    ]

    history_messages = await get_recent_history(
        session=session,
        tenant_id=tenant.id,
        session_id=body.session_id,
    )
    history_block = build_history_block(history_messages)

    logger.info("chat_stream_start", extra={
        "tenant_id": tenant.id,
        "query": body.query[:50],
        "history_turns": len(history_messages),
    })

    async def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        full_answer = ""
        async for token in async_generator(stream_llm, body.query, snippets, history_block):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Save to history after streaming completes
        await save_message(session, tenant.id, body.session_id, "user", body.query)
        await save_message(session, tenant.id, body.session_id, "assistant", full_answer)

        yield f"data: {json.dumps({'type': 'done', 'full_answer': full_answer})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )