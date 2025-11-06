"""Database dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

# Type alias for database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]
