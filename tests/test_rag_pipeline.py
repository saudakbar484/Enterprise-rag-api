import pytest
import uuid
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from main import app
from tests.conftest import override_get_session

# ── Constants ──
ADMIN_HEADERS = {"X-Admin-Token": "super-secret-admin-token"}
TEST_DOCUMENT = """
Pakistan Sweet Home is a welfare organization in Islamabad.
It provides shelter, education, healthcare, and social support
to orphaned and underprivileged children across Pakistan.
The organization was founded to create safe environments
where children can learn and develop into responsible citizens.
"""

MOCK_LLM_ANSWER = (
    "According to test_doc.txt, Pakistan Sweet Home provides "
    "shelter, education, healthcare, and social support services."
)


# ── Fixture: create tenant and return api_key ──
@pytest.fixture
async def pipeline_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def authenticated_tenant(pipeline_client):
    response = await pipeline_client.post(
        "/api/v1/tenants/",
        json={"name": "Pipeline Test Tenant"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "tenant_id": data["id"],
        "api_key": data["api_key"],
        "headers": {"X-Tenant-API-Key": data["api_key"]},
    }


# ── Test 1: Full pipeline — ingest → search → chat with mocked LLM ──
@pytest.mark.asyncio
async def test_full_rag_pipeline(pipeline_client, authenticated_tenant):
    headers = authenticated_tenant["headers"]

    # Step 1 — ingest document via Celery task directly (bypass async worker)
    with patch("app.api.v1.documents.ingest_document") as mock_task:
        mock_result = MagicMock()
        mock_result.id = str(uuid.uuid4())
        mock_task.delay.return_value = mock_result

        upload_response = await pipeline_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("pipeline_test.txt", TEST_DOCUMENT.encode(), "text/plain")},
        )
        assert upload_response.status_code == 202
        data = upload_response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data

    # Step 2 — directly embed and store test document for search
    with patch("app.api.v1.search.search_tenant_vectors") as mock_search:
        from app.services.search import SearchResult
        mock_search.return_value = [
            SearchResult(
                chunk_index=0,
                text=TEST_DOCUMENT.strip(),
                score=0.91,
                filename="pipeline_test.txt",
                tenant_id=authenticated_tenant["tenant_id"],
            )
        ]

        search_response = await pipeline_client.post(
            "/api/v1/search/",
            headers=headers,
            json={"query": "what does Pakistan Sweet Home provide", "limit": 3},
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0
        assert results[0]["score"] == 0.91
        assert "Pakistan Sweet Home" in results[0]["text"]

    # Step 3 — chat query with mocked LLM and mocked search
    with patch("app.api.v1.chat.search_tenant_vectors") as mock_search, \
         patch("app.api.v1.chat.query_llm") as mock_llm:

        from app.services.search import SearchResult
        mock_search.return_value = [
            SearchResult(
                chunk_index=0,
                text=TEST_DOCUMENT.strip(),
                score=0.91,
                filename="pipeline_test.txt",
                tenant_id=authenticated_tenant["tenant_id"],
            )
        ]
        mock_llm.return_value = MOCK_LLM_ANSWER

        chat_response = await pipeline_client.post(
            "/api/v1/chat/query",
            headers=headers,
            json={
                "query": "What services does Pakistan Sweet Home provide?",
                "session_id": f"test-session-{uuid.uuid4()}",
                "limit": 3,
            },
        )
        assert chat_response.status_code == 200
        data = chat_response.json()

        # Assert response structure
        assert "query" in data
        assert "answer" in data
        assert "sources" in data
        assert "tenant_id" in data
        assert "retrieval_ms" in data
        assert "llm_ms" in data

        # Assert LLM answer incorporates context
        assert data["answer"] == MOCK_LLM_ANSWER
        assert "Pakistan Sweet Home" in data["answer"]
        assert "shelter" in data["answer"]

        # Assert sources are correct
        assert len(data["sources"]) > 0
        assert data["sources"][0]["filename"] == "pipeline_test.txt"
        assert data["sources"][0]["score"] == 0.91

        # Assert tenant isolation
        assert data["tenant_id"] == authenticated_tenant["tenant_id"]


# ── Test 2: Search returns empty — LLM should get no context ──
@pytest.mark.asyncio
async def test_pipeline_no_context(pipeline_client, authenticated_tenant):
    headers = authenticated_tenant["headers"]

    with patch("app.api.v1.chat.search_tenant_vectors") as mock_search, \
         patch("app.api.v1.chat.query_llm") as mock_llm:

        mock_search.return_value = []
        mock_llm.return_value = "I cannot answer this question based on the available documents."

        response = await pipeline_client.post(
            "/api/v1/chat/query",
            headers=headers,
            json={
                "query": "What is the population of Mars?",
                "session_id": f"test-session-{uuid.uuid4()}",
                "limit": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "cannot answer" in data["answer"].lower()
        assert data["sources"] == []


# ── Test 3: Unauthorized request is rejected ──
@pytest.mark.asyncio
async def test_pipeline_unauthorized(pipeline_client):
    response = await pipeline_client.post(
        "/api/v1/chat/query",
        headers={"X-Tenant-API-Key": "totally-fake-key"},
        json={
            "query": "What services does Pakistan Sweet Home provide?",
            "session_id": "test-session",
            "limit": 3,
        },
    )
    assert response.status_code == 403


# ── Test 4: Verify tenant isolation — one tenant can't see another's data ──
@pytest.mark.asyncio
async def test_pipeline_tenant_isolation(pipeline_client):
    # Create two tenants
    r1 = await pipeline_client.post(
        "/api/v1/tenants/",
        json={"name": "Tenant Alpha"},
        headers=ADMIN_HEADERS,
    )
    r2 = await pipeline_client.post(
        "/api/v1/tenants/",
        json={"name": "Tenant Beta"},
        headers=ADMIN_HEADERS,
    )
    tenant_a = r1.json()
    tenant_b = r2.json()

    with patch("app.api.v1.chat.search_tenant_vectors") as mock_search, \
         patch("app.api.v1.chat.query_llm") as mock_llm:

        from app.services.search import SearchResult

        def search_side_effect(query, tenant_id, limit):
            # Each tenant only gets their own data
            return [
                SearchResult(
                    chunk_index=0,
                    text=f"Data belonging to tenant {tenant_id[:8]}",
                    score=0.85,
                    filename=f"doc_{tenant_id[:8]}.txt",
                    tenant_id=tenant_id,
                )
            ]

        mock_search.side_effect = search_side_effect
        mock_llm.return_value = "Answer based on tenant-specific context."

        # Tenant A query
        r_a = await pipeline_client.post(
            "/api/v1/chat/query",
            headers={"X-Tenant-API-Key": tenant_a["api_key"]},
            json={"query": "show me my data", "session_id": "s1", "limit": 3},
        )
        # Tenant B query
        r_b = await pipeline_client.post(
            "/api/v1/chat/query",
            headers={"X-Tenant-API-Key": tenant_b["api_key"]},
            json={"query": "show me my data", "session_id": "s2", "limit": 3},
        )

        assert r_a.status_code == 200
        assert r_b.status_code == 200

        # Each tenant gets their own tenant_id back
        assert r_a.json()["tenant_id"] == tenant_a["id"]
        assert r_b.json()["tenant_id"] == tenant_b["id"]

        # Tenant A's source should not appear in Tenant B's results
        assert r_a.json()["sources"][0]["filename"] != r_b.json()["sources"][0]["filename"]