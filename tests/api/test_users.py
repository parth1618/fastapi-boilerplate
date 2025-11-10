"""User endpoint tests."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
class TestGetCurrentUser:
    """Test get current user endpoint."""

    async def test_get_current_user_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting current user info."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "hashed_password" not in data

    async def test_get_current_user_unauthorized(self, client: AsyncClient) -> None:
        """Test getting current user without auth."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401

    async def test_get_current_user_invalid_token(
        self,
        client: AsyncClient,
        invalid_token: str,
    ) -> None:
        """Test with invalid token."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert response.status_code == 401

    async def test_get_current_user_expired_token(
        self,
        client: AsyncClient,
        expired_token: str,
    ) -> None:
        """Test with expired token."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateCurrentUser:
    """Test update current user endpoint."""

    async def test_update_full_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating full name."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    async def test_update_email(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating email."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"email": "newemail@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    async def test_update_duplicate_email(
        self,
        client: AsyncClient,
        test_user: User,
        test_admin: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating to existing email."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"email": test_admin.email},
        )

        assert response.status_code == 400

    async def test_update_password(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating password."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"password": "NewPassword123!"},  # pragma: allowlist secret
        )

        assert response.status_code == 200

    async def test_update_weak_password(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test updating to weak password."""
        response = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"password": "weak"},  # pragma: allowlist secret
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestListUsers:
    """Test list users endpoint."""

    async def test_list_users_as_admin(
        self,
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
        assert data["total"] >= 2
        assert isinstance(data["users"], list)

    async def test_list_users_as_regular_user(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing users as regular user (should fail)."""
        response = await client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 403

    async def test_list_users_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test pagination parameters."""
        response = await client.get(
            "/api/v1/users/?page=1&page_size=1",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    async def test_list_users_invalid_page(
        self,
        client: AsyncClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test with invalid page number."""
        response = await client.get(
            "/api/v1/users/?page=0",
            headers=admin_headers,
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestGetUser:
    """Test get user by ID endpoint."""

    async def test_get_user_as_admin(
        self,
        client: AsyncClient,
        test_user: User,
        admin_headers: dict[str, str],
    ) -> None:
        """Test getting user by ID as admin."""
        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    async def test_get_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test getting nonexistent user."""
        response = await client.get(
            "/api/v1/users/99999",
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_get_user_as_regular_user(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting user as regular user (should fail)."""
        response = await client.get(
            f"/api/v1/users/{test_admin.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestUpdateUser:
    """Test update user by ID endpoint."""

    async def test_update_user_as_admin(
        self,
        client: AsyncClient,
        test_user: User,
        admin_headers: dict[str, str],
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

    async def test_update_user_role(
        self,
        client: AsyncClient,
        test_user: User,
        admin_headers: dict[str, str],
    ) -> None:
        """Test updating user role."""
        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
            json={"role": "moderator"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "moderator"

    async def test_update_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test updating nonexistent user."""
        response = await client.put(
            "/api/v1/users/99999",
            headers=admin_headers,
            json={"full_name": "Test"},
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteUser:
    """Test delete user endpoint."""

    async def test_delete_user_as_admin(
        self,
        client: AsyncClient,
        test_user: User,
        admin_headers: dict[str, str],
    ) -> None:
        """Test deleting user as admin."""
        response = await client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200

        # Verify user is deleted
        get_response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_self(
        self,
        client: AsyncClient,
        test_admin: User,
        admin_headers: dict[str, str],
    ) -> None:
        """Test admin cannot delete themselves."""
        response = await client.delete(
            f"/api/v1/users/{test_admin.id}",
            headers=admin_headers,
        )

        assert response.status_code == 400

    async def test_delete_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test deleting nonexistent user."""
        response = await client.delete(
            "/api/v1/users/99999",
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_delete_user_as_regular_user(
        self,
        client: AsyncClient,
        test_admin: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test deleting user as regular user (should fail)."""
        response = await client.delete(
            f"/api/v1/users/{test_admin.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
