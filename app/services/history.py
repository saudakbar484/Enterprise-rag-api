import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.chat_message import ChatMessage
from app.core.logging import logger

HISTORY_TURNS = 5          # last N turns to fetch
TOKEN_BUDGET = 1500        # max tokens for history in prompt
SUMMARY_THRESHOLD = 1000   # summarize if history exceeds this

encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


async def save_message(
    session: AsyncSession,
    tenant_id: str,
    session_id: str,
    role: str,
    content: str,
) -> ChatMessage:
    token_count = count_tokens(content)
    message = ChatMessage(
        tenant_id=tenant_id,
        session_id=session_id,
        role=role,
        content=content,
        token_count=token_count,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_recent_history(
    session: AsyncSession,
    tenant_id: str,
    session_id: str,
    turns: int = HISTORY_TURNS,
) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.tenant_id == tenant_id)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(turns * 2)  # *2 because each turn = user + assistant
    )
    messages = result.scalars().all()
    return list(reversed(messages))  # chronological order


def summarize_history(messages: list[ChatMessage]) -> str:
    """
    Collapses history into a compact summary when token budget is tight.
    """
    lines = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        # Truncate long messages to first 200 chars in summary
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        lines.append(f"{role}: {content}")
    return "Previous conversation summary:\n" + "\n".join(lines)


def build_history_block(messages: list[ChatMessage]) -> str:
    """
    Builds history block for the prompt.
    Summarizes if token count exceeds budget.
    """
    if not messages:
        return ""

    # Calculate total tokens
    total_tokens = sum(m.token_count for m in messages)

    logger.info("history_block", extra={
        "message_count": len(messages),
        "total_tokens": total_tokens,
        "token_budget": TOKEN_BUDGET,
    })

    if total_tokens > SUMMARY_THRESHOLD:
        # Summarize to stay within budget
        summary = summarize_history(messages)
        logger.info("history_summarized", extra={
            "original_tokens": total_tokens,
            "summary_tokens": count_tokens(summary),
        })
        return summary

    # Full history within budget
    lines = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "Previous conversation:\n" + "\n".join(lines)