import uuid
from fastapi import APIRouter, Depends, File, UploadFile
from sentence_transformers import SentenceTransformer
from qdrant_client.models import PointStruct

from app.api.dependencies import get_current_tenant
from app.core.vector_store import client, COLLECTION_NAME
from app.models.tenant import Tenant
from app.services.parser import chunk_document

router = APIRouter()

_model = SentenceTransformer("all-MiniLM-L6-v2")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
):
    content = (await file.read()).decode("utf-8")
    chunks = chunk_document(content)

    texts = [c["text"] for c in chunks]
    embeddings = _model.encode(texts, batch_size=32)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i].tolist(),
            payload={
                "tenant_id": tenant.id,
                "text": chunks[i]["text"],
                "chunk_index": chunks[i]["chunk_index"],
                "token_count": chunks[i]["token_count"],
                "source_file": file.filename,
            },
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)

    return {
        "filename": file.filename,
        "chunks_stored": len(points),
        "tenant_id": tenant.id,
    }