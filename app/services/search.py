from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.core.vector_store import client, COLLECTION_NAME
from app.services.embedder import embed_texts
from app.services.reranker import rerank
from app.core.logging import logger
from dataclasses import dataclass

RETRIEVAL_LIMIT = 15  # fetch more, rerank down


@dataclass
class SearchResult:
    chunk_index: int
    text: str
    score: float
    filename: str
    tenant_id: str


def search_tenant_vectors(
    query: str,
    tenant_id: str,
    limit: int = 5,
) -> list[SearchResult]:

    # Step 1 — embed the query
    query_vector = embed_texts([query])[0]

    # Step 2 — strict tenant_id filter
    tenant_filter = Filter(
        must=[
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id),
            )
        ]
    )

    # Step 3 — fetch top 15 from Qdrant
    logger.info("vector_search", extra={
        "tenant_id": tenant_id,
        "query": query[:50],
        "retrieval_limit": RETRIEVAL_LIMIT,
        "final_limit": limit,
    })

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=tenant_filter,
        limit=RETRIEVAL_LIMIT,
        with_payload=True,
    )

    # Step 4 — map to SearchResult
    results = [
        SearchResult(
            chunk_index=r.payload.get("chunk_index", 0),
            text=r.payload.get("text", ""),
            score=r.score,
            filename=r.payload.get("doc_filename", r.payload.get("filename", "")),
            tenant_id=r.payload.get("tenant_id", ""),
        )
        for r in response.points
    ]

    # Step 5 — rerank and return top `limit`
    return rerank(query, results, top_k=limit)