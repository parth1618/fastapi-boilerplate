"""User management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.security import get_password_hash
from app.dependencies.auth import get_current_active_user, get_current_superuser
from app.dependencies.db import DBSession
from app.models.user import User as UserModel
from app.schemas.message import Message
from app.schemas.user import User, UserListResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
) -> UserModel:
    """Get current user information."""
    return current_user


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: DBSession,
) -> UserModel:
    """Update current user information."""
    # Update fields if provided
    if user_update.email is not None:
        # Check if email is already taken by another user
        result = await db.execute(
            select(UserModel).where(
                UserModel.email == user_update.email,
                UserModel.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = user_update.email

    if user_update.username is not None:
        # Check if username is already taken by another user
        result = await db.execute(
            select(UserModel).where(
                UserModel.username == user_update.username,
                UserModel.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        current_user.username = user_update.username

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.get("/", response_model=UserListResponse)
async def list_users(
    db: DBSession,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> UserListResponse:
    """List all users (admin only)."""
    # Count total users
    count_result = await db.execute(select(func.count(UserModel.id)))
    total = count_result.scalar_one()

    # Get paginated users
    offset = (page - 1) * page_size
    result = await db.execute(
        select(UserModel).offset(offset).limit(page_size).order_by(UserModel.created_at.desc())
    )
    users = result.scalars().all()

    # Calculate total pages
    pages = (total + page_size - 1) // page_size

    return UserListResponse(
        users=list(users),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: DBSession,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
) -> UserModel:
    """Get user by ID (admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: DBSession,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
) -> UserModel:
    """Update user by ID (admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields if provided
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.role is not None:
        user.role = user_update.role

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=Message)
async def delete_user(
    user_id: int,
    db: DBSession,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
) -> Message:
    """Delete user by ID (admin only)."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    await db.delete(user)
    await db.commit()

    return Message(message=f"User {user.username} deleted successfully")
