import uuid
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.services.parser import chunk_text
from app.services.embedder import embed_texts
from app.core.vector_store import client, COLLECTION_NAME
from qdrant_client.models import PointStruct


@celery_app.task(bind=True, name="ingest_document")
def ingest_document(self, text: str, doc_filename: str, tenant_id: str):
    try:
        # Stage 1
        self.update_state(state="PROGRESS", meta={
            "stage": "chunking",
            "progress": 10,
            "doc_filename": doc_filename,
        })
        logger.info("ingest_started", extra={
            "task_id": self.request.id,
            "tenant_id": tenant_id,
            "doc_filename": doc_filename,
        })
        chunks = chunk_text(text)

        # Stage 2
        self.update_state(state="PROGRESS", meta={
            "stage": "embedding",
            "progress": 40,
            "chunks": len(chunks),
            "doc_filename": doc_filename,
        })
        texts = [chunk.text for chunk in chunks]
        embeddings = embed_texts(texts)

        # Stage 3
        self.update_state(state="PROGRESS", meta={
            "stage": "storing",
            "progress": 80,
            "chunks": len(chunks),
            "doc_filename": doc_filename,
        })
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings[i],
                payload={
                    "tenant_id": tenant_id,
                    "doc_filename": doc_filename,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)

        logger.info("ingest_complete", extra={
            "task_id": self.request.id,
            "tenant_id": tenant_id,
            "chunks": len(chunks),
            "points_stored": len(points),
        })

        return {
            "status": "complete",
            "stage": "done",
            "progress": 100,
            "chunks": len(chunks),
            "points_stored": len(points),
            "doc_filename": doc_filename,
        }

    except Exception as e:
        logger.error("ingest_failed", extra={
            "task_id": self.request.id,
            "error": str(e),
        })
        raise