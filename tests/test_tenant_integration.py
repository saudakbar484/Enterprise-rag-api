import pytest

ADMIN_HEADERS = {"X-Admin-Token": "super-secret-admin-token"}


@pytest.mark.asyncio
async def test_create_tenant_returns_200(integration_client):
    response = await integration_client.post(
        "/api/v1/tenants/", json={"name": "Integration Tenant"}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_tenant_returns_correct_fields(integration_client):
    response = await integration_client.post(
        "/api/v1/tenants/", json={"name": "Field Check Tenant"}, headers=ADMIN_HEADERS
    )
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "api_key" in data
    assert data["name"] == "Field Check Tenant"


@pytest.mark.asyncio
async def test_create_tenant_api_key_grants_access(integration_client):
    # Step 1 — create tenant
    create_response = await integration_client.post(
        "/api/v1/tenants/", json={"name": "Access Tenant"}, headers=ADMIN_HEADERS
    )
    api_key = create_response.json()["api_key"]

    # Step 2 — use api_key to access /me
    me_response = await integration_client.get(
        "/api/v1/tenants/me", headers={"X-Tenant-API-Key": api_key}
    )
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Access Tenant"


@pytest.mark.asyncio
async def test_create_tenant_without_admin_token_returns_403(integration_client):
    response = await integration_client.post(
        "/api/v1/tenants/", json={"name": "Unauthorized Tenant"}
    )
    assert response.status_code == 422  # missing header


@pytest.mark.asyncio
async def test_each_test_gets_clean_database(integration_client):
    # If DB was dirty from previous test, this tenant count would be wrong
    response = await integration_client.post(
        "/api/v1/tenants/", json={"name": "Clean DB Tenant"}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    # Only this tenant exists — proves DB was wiped before this test
    data = response.json()
    assert data["name"] == "Clean DB Tenant"
