from __future__ import annotations
from typing import IO, Union
from transformers import AutoTokenizer

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50       # 10% of 500
STEP_TOKENS = CHUNK_TOKENS - OVERLAP_TOKENS  # 450
_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_tokenizer = None

def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL)
    return _tokenizer

def chunk_document(source: Union[str, IO[str]]) -> list[dict]:
    text = source.read() if hasattr(source, "read") else source

    tokenizer = _get_tokenizer()
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    total = len(token_ids)

    chunks = []
    start = 0

    while start < total:
        end = min(start + CHUNK_TOKENS, total)
        chunk_ids = token_ids[start:end]
        chunks.append({
            "chunk_index": len(chunks),
            "text": tokenizer.decode(chunk_ids, skip_special_tokens=True),
            "token_count": end - start,
            "token_start": start,
            "token_end": end,
        })
        if end == total:
            break
        start += STEP_TOKENS

    return chunks

