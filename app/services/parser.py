import tiktoken
from dataclasses import dataclass

CHUNK_SIZE = 500
OVERLAP = 50  # 10% of 500

@dataclass
class TextChunk:
    index: int
    text: str
    token_count: int
    start_token: int
    end_token: int


def get_encoder():
    return tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[TextChunk]:
    """
    Splits text into chunks of exactly `chunk_size` tokens
    with `overlap` tokens carried over between successive chunks.
    """
    encoder = get_encoder()
    tokens = encoder.encode(text)
    total_tokens = len(tokens)

    chunks = []
    start = 0
    index = 0

    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = encoder.decode(chunk_tokens)

        chunks.append(TextChunk(
            index=index,
            text=chunk_text,
            token_count=len(chunk_tokens),
            start_token=start,
            end_token=end,
        ))

        index += 1
        start += chunk_size - overlap  # move forward, keeping overlap

    return chunks