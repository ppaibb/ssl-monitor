import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import User, Session

settings = get_settings()
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_token() -> str:
    return secrets.token_hex(64)


async def create_session(user_id: int, db: AsyncSession) -> str:
    token = generate_token()
    expires = datetime.utcnow() + timedelta(days=settings.TOKEN_EXPIRE_DAYS)
    session = Session(token=token, user_id=user_id, expires_at=expires)
    db.add(session)
    await db.commit()
    return token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    result = await db.execute(
        select(Session).where(
            Session.token == token,
            Session.expires_at > datetime.utcnow(),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的 token")
    user = await db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
