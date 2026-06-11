import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm import query_llm

# ── Test 1: Answerable from context ──
print("="*60)
print("TEST 1 — Answerable from context")
print("="*60)

snippets = [
    {
        "filename": "test_doc.txt",
        "chunk_index": 0,
        "text": (
            "Pakistan Sweet Home (PSH) is a welfare organization "
            "located in Islamabad, Pakistan. It provides shelter, "
            "education, healthcare, and social support services to "
            "orphaned and underprivileged children."
        )
    }
]

query = "What services does Pakistan Sweet Home provide?"
answer = query_llm(query, snippets)
print(f"Query : {query}")
print(f"Answer: {answer}\n")

# ── Test 2: Out of scope question ──
print("="*60)
print("TEST 2 — Out of scope (hallucination guard)")
print("="*60)

query2 = "What is the capital of France?"
answer2 = query_llm(query2, snippets)
print(f"Query : {query2}")
print(f"Answer: {answer2}\n")

# ── Test 3: Empty context ──
print("="*60)
print("TEST 3 — No context available")
print("="*60)

query3 = "Tell me about the organization's funding sources."
answer3 = query_llm(query3, [])
print(f"Query : {query3}")
print(f"Answer: {answer3}\n")