from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import get_current_user
from database import get_db
from models import User, Webhook
from notifier import send_webhook
from schemas import WebhookIn, WebhookOut, WebhookTestOut

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

VALID_TYPES = {"wecom", "dingtalk", "custom"}


@router.get("", response_model=list[WebhookOut])
async def list_webhooks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).where(Webhook.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=WebhookOut)
async def create_webhook(body: WebhookIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"type 必须是 {VALID_TYPES}")
    wh = Webhook(user_id=user.id, **body.model_dump())
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.patch("/{wh_id}", response_model=WebhookOut)
async def update_webhook(
    wh_id: int,
    body: WebhookIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wh = await _get_owned(wh_id, user.id, db)
    for k, v in body.model_dump().items():
        setattr(wh, k, v)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete("/{wh_id}")
async def delete_webhook(wh_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wh = await _get_owned(wh_id, user.id, db)
    await db.delete(wh)
    await db.commit()
    return {"ok": True}


@router.post("/{wh_id}/test", response_model=WebhookTestOut)
async def test_webhook(wh_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wh = await _get_owned(wh_id, user.id, db)
    fake_result = {
        "domain": "example.com",
        "port": 443,
        "days_left": 7,
        "not_after": "2026-03-06",
        "issuer_cn": "Let's Encrypt",
        "is_expired": False,
        "is_expiring_soon": True,
        "error": None,
    }
    ok, err = await send_webhook(wh, fake_result)
    return {"ok": ok, "error": err}


async def _get_owned(wh_id: int, user_id: int, db: AsyncSession) -> Webhook:
    wh = await db.get(Webhook, wh_id)
    if not wh or wh.user_id != user_id:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    return wh
