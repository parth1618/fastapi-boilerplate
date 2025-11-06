"""Tests for user endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_get_current_user(
    client: AsyncClient, test_user: User, auth_headers: dict[str, str]
) -> None:
    """Test getting current user information."""
    response = await client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient) -> None:
    """Test getting current user without authentication."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_current_user(
    client: AsyncClient, test_user: User, auth_headers: dict[str, str]
) -> None:
    """Test updating current user."""
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_list_users_as_admin(
    client: AsyncClient,
    test_user: User,
    test_admin: User,
    admin_headers: dict[str, str],
) -> None:
    """Test listing users as admin."""
    response = await client.get("/api/v1/users/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 2  # At least test_user and test_admin


@pytest.mark.asyncio
async def test_list_users_as_regular_user(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test listing users as regular user (should fail)."""
    response = await client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id_as_admin(
    client: AsyncClient, test_user: User, admin_headers: dict[str, str]
) -> None:
    """Test getting user by ID as admin."""
    response = await client.get(f"/api/v1/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id


@pytest.mark.asyncio
async def test_update_user_as_admin(
    client: AsyncClient, test_user: User, admin_headers: dict[str, str]
) -> None:
    """Test updating user as admin."""
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers=admin_headers,
        json={"full_name": "Admin Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Admin Updated Name"


@pytest.mark.asyncio
async def test_delete_user_as_admin(
    client: AsyncClient, test_user: User, admin_headers: dict[str, str]
) -> None:
    """Test deleting user as admin."""
    response = await client.delete(f"/api/v1/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200

    # Verify user is deleted
    get_response = await client.get(f"/api/v1/users/{test_user.id}", headers=admin_headers)
    assert get_response.status_code == 404
