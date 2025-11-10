"""Enhanced user Pydantic schemas with comprehensive validation."""

import re
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.config import settings

# Base Schemas


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 chars, alphanumeric, _, -)",
        examples=["johndoe", "jane_smith"],
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="User's full name",
        examples=["John Doe"],
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active",
    )
    role: str = Field(
        default="user",
        description="User role",
        examples=["user", "admin", "moderator"],
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        """Validate full name format."""
        if v is None:
            return v

        # Remove excessive whitespace
        v = " ".join(v.split())

        # Check for invalid characters
        if not re.match(r"^[a-zA-Z\s'-]+$", v):
            raise ValueError("Full name can only contain letters, spaces, hyphens, and apostrophes")

        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate user role."""
        valid_roles = {"user", "admin", "moderator", "staff"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


# Request Schemas


class UserCreate(BaseModel):
    """Schema for user registration/creation."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 chars)",
        examples=["johndoe"],
    )
    password: str = Field(
        ...,
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description=f"Password (min {settings.PASSWORD_MIN_LENGTH} chars)",
        examples=["StrongP@ssw0rd!"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="User's full name",
        examples=["John Doe"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format and restrictions."""
        # Check length
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")

        # Check format
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with alphanumeric and contain only "
                "letters, numbers, underscores, and hyphens"
            )

        # Check for reserved usernames
        reserved_usernames = {
            "admin",
            "root",
            "system",
            "api",
            "www",
            "mail",
            "support",
            "info",
            "help",
            "moderator",
            "administrator",
        }
        if v.lower() in reserved_usernames:
            raise ValueError(f"Username '{v}' is reserved")

        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        min_length = settings.PASSWORD_MIN_LENGTH

        # Check minimum length
        if len(v) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")

        # Check maximum length
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters long")

        # Check complexity requirements
        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if settings.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        # Check for common passwords
        common_passwords = {
            "password",
            "password123",
            "12345678",
            "qwerty",
            "abc123",
            "admin",
            "admin123",
            "letmein",
            "welcome",
            "monkey",
        }
        if v.lower() in common_passwords:
            raise ValueError("Password is too common, please choose a stronger password")

        # Check for username in password (if username provided)
        # This would need to be done at the service layer with full context

        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: EmailStr | None = Field(
        default=None,
        description="New email address",
        examples=["newemail@example.com"],
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="New username",
        examples=["new_username"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="New full name",
        examples=["Jane Doe"],
    )
    password: str | None = Field(
        default=None,
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="New password",
    )
    is_active: bool | None = Field(
        default=None,
        description="Update active status (admin only)",
    )
    role: str | None = Field(
        default=None,
        description="Update user role (admin only)",
        examples=["user", "admin"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username if provided."""
        if v is None:
            return v

        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with alphanumeric and contain only "
                "letters, numbers, underscores, and hyphens"
            )

        # Check for reserved usernames for updates too
        reserved_usernames = {
            "admin",
            "root",
            "system",
            "api",
            "www",
            "mail",
            "support",
            "info",
            "help",
            "moderator",
            "administrator",
        }
        if v.lower() in reserved_usernames:
            raise ValueError(f"Username '{v}' is reserved")

        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Validate password if provided."""
        if v is None:
            return v

        min_length = settings.PASSWORD_MIN_LENGTH

        if len(v) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")

        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if settings.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Validate role if provided."""
        if v is None:
            return v

        valid_roles = {"user", "admin", "moderator", "staff"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(
        ...,
        description="Current password",
        min_length=1,
    )
    new_password: str = Field(
        ...,
        description="New password",
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
    )
    confirm_password: str = Field(
        ...,
        description="Confirm new password",
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        min_length = settings.PASSWORD_MIN_LENGTH

        if len(v) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")

        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if settings.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "PasswordChange":
        """Validate that new password and confirmation match."""
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match")

        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")

        return self


# Response Schemas


class User(UserBase):
    """Schema for user response (read operations)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="User ID")
    is_superuser: bool = Field(..., description="Whether user is a superuser")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional fields for enhanced info
    last_login_at: datetime | None = Field(
        default=None,
        description="Last login timestamp",
    )
    email_verified: bool = Field(
        default=False,
        description="Whether email is verified",
    )
    mfa_enabled: bool = Field(
        default=False,
        description="Whether MFA is enabled",
    )


class UserInDB(User):
    """Schema for user in database (includes sensitive fields)."""

    hashed_password: str = Field(..., description="Hashed password")
    password_changed_at: datetime | None = Field(
        default=None,
        description="When password was last changed",
    )
    failed_login_attempts: int = Field(
        default=0,
        description="Number of failed login attempts",
    )
    account_locked_until: datetime | None = Field(
        default=None,
        description="Account lockout expiration",
    )


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    users: list[User] = Field(..., description="List of users")
    total: int = Field(..., ge=0, description="Total number of users")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class UserProfile(BaseModel):
    """Extended user profile with additional information."""

    model_config = ConfigDict(from_attributes=True)

    user: User = Field(..., description="User information")
    statistics: dict[str, int] = Field(
        default_factory=dict,
        description="User statistics",
        examples=[{"login_count": 42, "posts": 10}],
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences",
        examples=[{"theme": "dark", "language": "en"}],
    )


# Admin Schemas


class UserAdminUpdate(UserUpdate):
    """Extended update schema for admin operations."""

    is_superuser: bool | None = Field(
        default=None,
        description="Update superuser status (super admin only)",
    )
    force_password_change: bool | None = Field(
        default=None,
        description="Force user to change password on next login",
    )
    email_verified: bool | None = Field(
        default=None,
        description="Update email verification status",
    )


class UserBulkAction(BaseModel):
    """Schema for bulk user actions."""

    user_ids: list[int] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of user IDs",
    )
    action: str = Field(
        ...,
        pattern=r"^(activate|deactivate|delete|assign_role)$",
        description="Action to perform",
        examples=["activate", "deactivate"],
    )
    role: str | None = Field(
        default=None,
        description="Role to assign (for assign_role action)",
    )

    @model_validator(mode="after")
    def validate_action_params(self) -> "UserBulkAction":
        """Validate action-specific parameters."""
        if self.action == "assign_role" and not self.role:
            raise ValueError("Role must be specified for assign_role action")
        return self
