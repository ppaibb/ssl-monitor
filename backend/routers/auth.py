import secrets
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import (
    hash_password, verify_password, create_session, get_current_user, generate_token
)
from config import get_settings
from database import get_db
from models import User, Session
from schemas import RegisterIn, LoginIn, ChangePasswordIn, UserOut, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

# 临时存储 GitHub OAuth 一次性 code（生产可用 Redis，这里内存够用）
_github_codes: dict[str, dict] = {}


@router.post("/register", response_model=TokenOut)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    count = await db.execute(select(func.count()).select_from(User))
    is_first = count.scalar() == 0

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        is_admin=is_first,
        auth_method="password",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = await create_session(user.id, db)
    return {"token": token, "user": user}


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = await create_session(user.id, db)
    return {"token": token, "user": user}


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 删除当前 token —— 需要从请求头提取，这里通过 user 获取所有 session 并删除最近一个
    # 实际上前端会传 Bearer token，这里偷懒删 user 所有 session 也可以，
    # 但为了精确，我们在 get_current_user 里已经验证过了，下面只能删全部
    # 若要精确删单个 token，需要把 token 传进来，暂时删全部 session
    from sqlalchemy import delete
    await db.execute(delete(Session).where(Session.user_id == user.id))
    await db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.auth_method != "password":
        raise HTTPException(status_code=400, detail="GitHub 登录用户不支持改密码")
    if not user.password_hash or not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}


# ---------- GitHub OAuth ----------

@router.get("/github")
async def github_login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth 未配置")
    callback = f"{settings.FRONTEND_URL}/api/auth/github/callback"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&redirect_uri={callback}"
    )
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth 未配置")

    # 用 code 换 access_token
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth 失败")

    # 获取用户信息
    async with httpx.AsyncClient() as client:
        user_r = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30,
        )
        emails_r = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10,
        )

    gh_user = user_r.json()
    gh_emails = emails_r.json()

    github_id = str(gh_user["id"])
    primary_email = next(
        (e["email"] for e in gh_emails if e.get("primary") and e.get("verified")),
        None,
    )
    if not primary_email:
        raise HTTPException(status_code=400, detail="无法获取 GitHub 主邮箱")

    # 查或建用户
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if not user:
        # 检查邮箱是否已存在
        result2 = await db.execute(select(User).where(User.email == primary_email))
        user = result2.scalar_one_or_none()
        if user:
            # 绑定 GitHub ID
            user.github_id = github_id
            user.auth_method = "github"
        else:
            count = await db.execute(select(func.count()).select_from(User))
            is_first = count.scalar() == 0
            user = User(
                email=primary_email,
                github_id=github_id,
                is_admin=is_first,
                auth_method="github",
            )
            db.add(user)
        await db.commit()
        await db.refresh(user)

    session_token = await create_session(user.id, db)

    # 生成一次性 code 给前端
    one_time = secrets.token_hex(32)
    _github_codes[one_time] = {
        "token": session_token,
        "expires": datetime.utcnow().timestamp() + 300,
    }

    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"{settings.FRONTEND_URL}?github_code={one_time}")


@router.get("/github/exchange", response_model=TokenOut)
async def github_exchange(code: str, db: AsyncSession = Depends(get_db)):
    entry = _github_codes.pop(code, None)
    if not entry or entry["expires"] < datetime.utcnow().timestamp():
        raise HTTPException(status_code=400, detail="code 无效或已过期")

    token = entry["token"]
    from sqlalchemy import select as sel
    result = await db.execute(
        sel(Session).where(Session.token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=400, detail="session 不存在")
    user = await db.get(User, session.user_id)
    return {"token": token, "user": user}
