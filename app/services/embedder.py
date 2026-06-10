from sentence_transformers import SentenceTransformer
from app.core.logging import logger

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    logger.info("generating_embeddings", extra={"count": len(texts)})
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()