import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client.models import PointStruct
from app.core.database import get_session
from app.core.vector_store import client, COLLECTION_NAME
from app.api.dependencies import get_current_tenant
from app.services.parser import chunk_text
from app.services.embedder import embed_texts
from app.models.tenant import Tenant
from app.core.logging import logger

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    # Step 1 — read uploaded file
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

   # Step 2 — chunk the text
    chunks = chunk_text(text)
    logger.info("document_chunked", extra={
        "tenant_id": tenant.id,
        "doc_filename": file.filename,   # renamed
        "chunks": len(chunks)
    })

    # Step 3 — embed all chunks in one batch
    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)

    # Step 4 — build Qdrant points with tenant_id in payload
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i],
            payload={
                "tenant_id": tenant.id,
                "doc_filename": file.filename,
                "chunk_index": chunk.index,
                "text": chunk.text,
                "token_count": chunk.token_count,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    # Step 5 — upsert into Qdrant
    client.upsert(collection_name=COLLECTION_NAME, points=points)

    logger.info("document_uploaded", extra={
        "tenant_id": tenant.id,
        "doc_filename": file.filename,
        "points_stored": len(points)
    })

    return {
        "doc_filename": file.filename,
        "chunks": len(chunks),
        "points_stored": len(points),
        "tenant_id": tenant.id,
    }