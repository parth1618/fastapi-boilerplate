"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies.db import DBSession
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import User, UserCreate
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DBSession) -> User:
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
) -> Token:
    """Login and get access token."""
    auth_service = AuthService(db)
    return await auth_service.authenticate_user(form_data.username, form_data.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: DBSession,
) -> Token:
    """Refresh access token."""
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(token_data.refresh_token)
