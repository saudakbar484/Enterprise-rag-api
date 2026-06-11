import ollama
from typing import Generator
from app.core.config import settings
from app.core.logging import logger

OLLAMA_MODEL = "llama3.2"

SYSTEM_PROMPT = """You are a precise, factual assistant for an enterprise knowledge base.

STRICT RULES YOU MUST FOLLOW:
1. Answer ONLY using information explicitly present in the provided context snippets.
2. If the context does not contain enough information to answer, respond with exactly:
   "I cannot answer this question based on the available documents."
3. Never speculate, infer, or use knowledge outside the provided context.
4. Never make up facts, names, numbers, or dates.
5. Do not answer general knowledge questions — only questions answerable from context.
6. If the user asks something unrelated to the context, say:
   "This question is outside the scope of the provided documents."
7. Always cite which part of the context you used by referencing the filename.
8. Keep answers concise and factual.

CONTEXT FORMAT:
You will receive numbered context snippets, each tagged with a source filename.
Use only these snippets to construct your answer.
"""


def build_context_block(snippets: list[dict]) -> str:
    if not snippets:
        return "No context available."
    lines = []
    for i, snippet in enumerate(snippets, 1):
        lines.append(
            f"[{i}] Source: {snippet.get('filename', 'unknown')} "
            f"(chunk {snippet.get('chunk_index', 0)})\n"
            f"{snippet.get('text', '').strip()}"
        )
    return "\n\n".join(lines)


def build_messages(
    query: str,
    snippets: list[dict],
    history_block: str = "",
) -> list[dict]:
    context_block = build_context_block(snippets)

    # Inject history into user message if available
    history_section = ""
    if history_block:
        history_section = f"CONVERSATION HISTORY:\n{history_block}\n\n"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"{history_section}"
                f"CONTEXT SNIPPETS:\n\n{context_block}\n\n"
                f"QUESTION: {query}"
            ),
        },
    ]


def query_llm(
    query: str,
    snippets: list[dict],
    history_block: str = "",
) -> str:
    messages = build_messages(query, snippets, history_block)

    logger.info("llm_request", extra={
        "model": OLLAMA_MODEL,
        "query": query[:50],
        "snippets_count": len(snippets),
        "has_history": bool(history_block),
    })

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": 0.0},
    )

    answer = response["message"]["content"].strip()

    logger.info("llm_response", extra={
        "model": OLLAMA_MODEL,
        "answer_preview": answer[:80],
    })

    return answer


def stream_llm(
    query: str,
    snippets: list[dict],
    history_block: str = "",
) -> Generator[str, None, None]:
    messages = build_messages(query, snippets, history_block)

    logger.info("llm_stream_request", extra={
        "model": OLLAMA_MODEL,
        "query": query[:50],
        "snippets_count": len(snippets),
    })

    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        stream=True,
        options={"temperature": 0.0},
    )

    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token