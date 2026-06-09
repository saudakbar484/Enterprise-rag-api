import pytest

@pytest.mark.asyncio
async def test_invalid_api_key_returns_403(client):
    response = await client.get(
        "/api/v1/tenants/me",
        headers={"X-Tenant-API-Key": "invalid-key-999"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_missing_api_key_returns_422(client):
    response = await client.get("/api/v1/tenants/me")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_valid_api_key_returns_tenant(client, tenant_api_key):
    response = await client.get(
        "/api/v1/tenants/me",
        headers={"X-Tenant-API-Key": tenant_api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tenant"
    assert "id" in data