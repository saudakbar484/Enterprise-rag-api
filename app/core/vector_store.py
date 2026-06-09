from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PayloadSchemaType,
)
from app.core.config import settings
from app.core.logging import logger

COLLECTION_NAME = "tenant_documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output size

client = QdrantClient(url=settings.qdrant_url)


def init_vector_store():
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        logger.info("vector_store_exists", extra={"collection": COLLECTION_NAME})
        return

    # Create collection with vector config
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    # Create strict keyword index on tenant_id payload field
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="tenant_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    logger.info("vector_store_created", extra={
        "collection": COLLECTION_NAME,
        "vector_size": VECTOR_SIZE,
        "distance": "cosine",
        "indexed_field": "tenant_id"
    })