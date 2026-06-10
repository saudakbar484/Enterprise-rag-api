from sentence_transformers import CrossEncoder
from app.core.logging import logger

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
reranker = CrossEncoder(RERANKER_MODEL)


def rerank(query: str, results: list, top_k: int = 5) -> list:
    """
    Takes a query and a list of SearchResult objects,
    re-scores them using a CrossEncoder, returns top_k.
    """
    if not results:
        return []

    # Build (query, passage) pairs for cross-encoder
    pairs = [(query, r.text) for r in results]

    # Score all pairs
    scores = reranker.predict(pairs)

    # Attach rerank score to each result
    scored = list(zip(results, scores))

    # Sort by rerank score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top_k
    top_results = [r for r, _ in scored[:top_k]]

    logger.info("reranking_complete", extra={
        "input_count": len(results),
        "output_count": len(top_results),
        "top_score": float(scored[0][1]) if scored else 0,
    })

    return top_results