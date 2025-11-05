"""User Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Base schema
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str | None = None
    is_active: bool = True
    role: str = "user"


# Schema for creating a user
class UserCreate(BaseModel):
    """Schema for user creation."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = None


# Schema for updating a user
class UserUpdate(BaseModel):
    """Schema for user update."""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50)
    full_name: str | None = None
    password: str | None = Field(None, min_length=8, max_length=100)
    is_active: bool | None = None
    role: str | None = None


# Schema for returning user data (response)
class User(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# Schema for user in database (includes hashed password)
class UserInDB(User):
    """Schema for user in database."""

    hashed_password: str


# Schema for paginated user list
class UserListResponse(BaseModel):
    """Schema for paginated user list."""

    users: list[User]
    total: int
    page: int
    page_size: int
    pages: int
