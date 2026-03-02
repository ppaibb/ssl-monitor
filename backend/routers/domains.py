import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import get_current_user
from checker import check_cert, check_certs_concurrent, serialize_san, deserialize_san
from database import get_db
from models import User, Domain, CertResult, Webhook, DomainWebhook
from notifier import notify_single
from schemas import (
    DomainIn, DomainOut, CertResultOut, DomainWebhookItem, DomainWebhookOut,
    BatchDomainIdsIn, BatchWebhookIn
)

router = APIRouter(prefix="/api/domains", tags=["domains"])


class BatchImportIn(BaseModel):
    lines: str  # 每行一个 domain 或 domain:port，前端传原始文本


@router.get("", response_model=list[DomainOut])
async def list_domains(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Domain).where(Domain.user_id == user.id))
    return [DomainOut.model_validate(d) for d in result.scalars().all()]


@router.post("", response_model=DomainOut)
async def add_domain(body: DomainIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    domain = body.domain.strip().lower()
    exists = await db.execute(
        select(Domain).where(Domain.user_id == user.id, Domain.domain == domain, Domain.port == body.port)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="域名已存在")

    d = Domain(
        user_id=user.id, 
        name=body.name,
        domain=domain, 
        port=body.port, 
        note=body.note, 
        tags=json.dumps(body.tags)
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return DomainOut.model_validate(d)


@router.put("/{domain_id}", response_model=DomainOut)
async def update_domain(domain_id: int, body: DomainIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Domain).where(Domain.id == domain_id, Domain.user_id == user.id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="域名不存在")
    d.name = body.name
    d.note = body.note
    d.tags = json.dumps(body.tags)
    await db.commit()
    await db.refresh(d)
    return DomainOut.model_validate(d)


@router.delete("")
async def delete_domain(
    domain: str,
    port: int = 443,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    domain = domain.strip().lower()
    result = await db.execute(
        select(Domain).where(Domain.user_id == user.id, Domain.domain == domain, Domain.port == port)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="域名不存在")
    await db.delete(d)
    # 同时清除该域名的检测记录
    await db.execute(
        delete(CertResult).where(
            CertResult.user_id == user.id,
            CertResult.domain == domain,
            CertResult.port == port,
        )
    )
    await db.commit()
    return {"ok": True}


@router.delete("/batch")
async def delete_batch(
    body: BatchDomainIdsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量删除域名及其检测记录"""
    if not body.domain_ids:
        return {"ok": True, "deleted": 0}

    # 首先查出所有属于该用户的域名（做权限隔离校验）
    result = await db.execute(
        select(Domain).where(Domain.id.in_(body.domain_ids), Domain.user_id == user.id)
    )
    domains = result.scalars().all()
    if not domains:
        return {"ok": True, "deleted": 0}

    domain_ids_to_delete = [d.id for d in domains]
    
    # 构建待清理的检测记录条件
    delete_cert_conds = [(d.domain, d.port) for d in domains]

    # 删除域名
    await db.execute(delete(Domain).where(Domain.id.in_(domain_ids_to_delete)))
    
    # 清理检测记录
    for dom, port in delete_cert_conds:
        await db.execute(
            delete(CertResult).where(
                CertResult.user_id == user.id,
                CertResult.domain == dom,
                CertResult.port == port,
            )
        )
    
    await db.commit()
    return {"ok": True, "deleted": len(domain_ids_to_delete)}


@router.get("/results", response_model=list[CertResultOut])
async def get_results(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CertResult)
        .where(CertResult.user_id == user.id)
        .order_by(CertResult.checked_at.desc())
    )
    rows = result.scalars().all()
    out = []
    for r in rows:
        d = r.__dict__.copy()
        d["san"] = deserialize_san(r.san)
        out.append(d)
    return out


@router.get("/history")
async def get_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """返回每个域名最近 60 次检测记录，供前端历史色块展示"""
    result = await db.execute(
        select(CertResult)
        .where(CertResult.user_id == user.id)
        .order_by(CertResult.domain, CertResult.port, CertResult.checked_at.desc())
    )
    grouped: dict[str, list] = {}
    for r in result.scalars().all():
        key = f"{r.domain}:{r.port}"
        if key not in grouped:
            grouped[key] = []
        if len(grouped[key]) < 60:
            grouped[key].append({
                "checked_at": r.checked_at.isoformat(),
                "days_left": r.days_left,
                "is_expired": r.is_expired,
                "is_expiring_soon": r.is_expiring_soon,
                "error": r.error,
            })
    return grouped


@router.get("/check", response_model=list[CertResultOut])
async def check_now(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    domains_result = await db.execute(select(Domain).where(Domain.user_id == user.id))
    domains = domains_result.scalars().all()
    if not domains:
        return []

    targets = [(d.domain, d.port) for d in domains]
    results = await check_certs_concurrent(targets)

    now = datetime.utcnow()
    cr_list = []
    for res in results:
        cr = CertResult(
            user_id=user.id,
            checked_at=now,
            san=serialize_san(res.get("san")),
            **{k: v for k, v in res.items() if k != "san"},
        )
        db.add(cr)
        cr_list.append(cr)
    await db.flush()
    # 保留最近 60 条历史
    for res in results:
        subq = (
            select(CertResult.id)
            .where(CertResult.user_id == user.id, CertResult.domain == res["domain"], CertResult.port == res["port"])
            .order_by(CertResult.checked_at.desc())
            .offset(60)
        )
        await db.execute(delete(CertResult).where(CertResult.id.in_(subq)))
    await db.commit()
    for cr in cr_list:
        await db.refresh(cr)
    return cr_list


@router.post("/batch", response_model=dict)
async def batch_import(
    body: BatchImportIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量导入域名，每行格式：domain 或 domain:port [备注]"""
    added, skipped, failed = [], [], []
    for raw in body.lines.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split(None, 1)  # 以空白分隔，最多 2 段（域名 + 可选备注/标签）
        domain_part = parts[0]
        note_raw = parts[1] if len(parts) > 1 else ""
        
        note = None
        tags = []
        if "#" in note_raw:
            n_part, t_part = note_raw.split("#", 1)
            note = n_part.strip() or None
            tags = [t.strip() for t in t_part.split(",") if t.strip()]
        else:
            note = note_raw.strip() or None

        # 解析 domain:port
        if ":" in domain_part:
            try:
                host, port_str = domain_part.rsplit(":", 1)
                port = int(port_str)
            except ValueError:
                failed.append(raw)
                continue
        else:
            host, port = domain_part, 443

        host = host.lower()
        if not host:
            failed.append(raw)
            continue

        exists = await db.execute(
            select(Domain).where(Domain.user_id == user.id, Domain.domain == host, Domain.port == port)
        )
        if exists.scalar_one_or_none():
            skipped.append(f"{host}:{port}")
            continue

        db.add(Domain(user_id=user.id, domain=host, port=port, note=note, tags=json.dumps(tags)))
        added.append(f"{host}:{port}")

    await db.commit()
    return {"added": len(added), "skipped": len(skipped), "failed": len(failed), "details": added}


@router.get("/check-one", response_model=CertResultOut)
async def check_one(
    domain: str,
    port: int = 443,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检测单个域名并更新结果，同时触发域名级 Webhook 告警"""
    domain = domain.strip().lower()

    # 确认域名属于当前用户
    dom_result = await db.execute(
        select(Domain).where(Domain.user_id == user.id, Domain.domain == domain, Domain.port == port)
    )
    dom_obj = dom_result.scalar_one_or_none()

    res = await check_cert(domain, port)
    now = datetime.utcnow()

    cr = CertResult(
        user_id=user.id,
        checked_at=now,
        san=serialize_san(res.get("san")),
        **{k: v for k, v in res.items() if k != "san"},
    )
    db.add(cr)
    await db.flush()
    subq = (
        select(CertResult.id)
        .where(CertResult.user_id == user.id, CertResult.domain == domain, CertResult.port == port)
        .order_by(CertResult.checked_at.desc())
        .offset(60)
    )
    await db.execute(delete(CertResult).where(CertResult.id.in_(subq)))
    await db.commit()
    await db.refresh(cr)

    # 触发告警
    if dom_obj:
        dw_result = await db.execute(
            select(DomainWebhook, Webhook)
            .join(Webhook, DomainWebhook.webhook_id == Webhook.id)
            .where(DomainWebhook.domain_id == dom_obj.id)
        )
        domain_whs = dw_result.all()
        global_wh_result = await db.execute(
            select(Webhook).where(Webhook.user_id == user.id, Webhook.enabled == True)
        )
        global_whs = global_wh_result.scalars().all()
        res_with_san = dict(res, san=res.get("san") or [], checked_at=now)
        await notify_single(domain_whs, global_whs, res_with_san)

    return cr


@router.post("/check-batch", response_model=list[CertResultOut])
async def check_batch(
    body: BatchDomainIdsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量检测传入的域名 ID"""
    if not body.domain_ids:
        return []

    # 只查属于当前用户的域名
    domains_result = await db.execute(
        select(Domain).where(Domain.id.in_(body.domain_ids), Domain.user_id == user.id)
    )
    domains = domains_result.scalars().all()
    if not domains:
        return []

    targets = [(d.domain, d.port) for d in domains]
    results = await check_certs_concurrent(targets)

    now = datetime.utcnow()
    cr_list = []
    
    # 保存结果并触发告警机制
    for res in results:
        cr = CertResult(
            user_id=user.id,
            checked_at=now,
            san=serialize_san(res.get("san")),
            **{k: v for k, v in res.items() if k != "san"},
        )
        db.add(cr)
        cr_list.append(cr)
    
    await db.flush()
    
    # 保留最近 60 条历史和发送告警通知
    for i, res in enumerate(results):
        dom_obj = next((d for d in domains if d.domain == res["domain"] and d.port == res["port"]), None)
        subq = (
            select(CertResult.id)
            .where(CertResult.user_id == user.id, CertResult.domain == res["domain"], CertResult.port == res["port"])
            .order_by(CertResult.checked_at.desc())
            .offset(60)
        )
        await db.execute(delete(CertResult).where(CertResult.id.in_(subq)))
        
        if dom_obj:
            dw_result = await db.execute(
                select(DomainWebhook, Webhook)
                .join(Webhook, DomainWebhook.webhook_id == Webhook.id)
                .where(DomainWebhook.domain_id == dom_obj.id)
            )
            domain_whs = dw_result.all()
            global_wh_result = await db.execute(
                select(Webhook).where(Webhook.user_id == user.id, Webhook.enabled == True)
            )
            global_whs = global_wh_result.scalars().all()
            res_with_san = dict(res, san=res.get("san") or [], checked_at=now)
            await notify_single(domain_whs, global_whs, res_with_san)

    await db.commit()
    for cr in cr_list:
        await db.refresh(cr)
    return cr_list


# ---------- 域名级 Webhook 绑定 ----------

async def _get_domain(domain_id: int, user_id: int, db: AsyncSession) -> Domain:
    d = await db.get(Domain, domain_id)
    if not d or d.user_id != user_id:
        raise HTTPException(status_code=404, detail="域名不存在")
    return d


@router.get("/{domain_id}/webhooks", response_model=list[DomainWebhookOut])
async def list_domain_webhooks(
    domain_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_domain(domain_id, user.id, db)
    result = await db.execute(
        select(DomainWebhook, Webhook)
        .join(Webhook, DomainWebhook.webhook_id == Webhook.id)
        .where(DomainWebhook.domain_id == domain_id)
    )
    rows = result.all()
    return [
        {
            "id": dw.id,
            "webhook_id": wh.id,
            "webhook_name": wh.name,
            "webhook_type": wh.type,
            "threshold_days": dw.threshold_days,
            "effective_threshold": dw.threshold_days if dw.threshold_days is not None else wh.threshold_days,
            "enabled": dw.enabled,
        }
        for dw, wh in rows
    ]


@router.put("/{domain_id}/webhooks")
async def set_domain_webhooks(
    domain_id: int,
    body: list[DomainWebhookItem],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """全量替换域名的 Webhook 绑定"""
    await _get_domain(domain_id, user.id, db)

    # 验证 webhook 都属于当前用户
    if body:
        wh_ids = [b.webhook_id for b in body]
        owned = await db.execute(
            select(Webhook.id).where(Webhook.id.in_(wh_ids), Webhook.user_id == user.id)
        )
        owned_ids = {r for r, in owned.all()}
        for b in body:
            if b.webhook_id not in owned_ids:
                raise HTTPException(status_code=400, detail=f"Webhook {b.webhook_id} 不存在")

    # 清旧绑定
    await db.execute(delete(DomainWebhook).where(DomainWebhook.domain_id == domain_id))

    # 写新绑定
    for b in body:
        db.add(DomainWebhook(
            domain_id=domain_id,
            webhook_id=b.webhook_id,
            threshold_days=b.threshold_days,
            enabled=b.enabled,
        ))
    await db.commit()
    return {"ok": True}


@router.put("/batch/webhooks")
async def set_batch_webhooks(
    body: BatchWebhookIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量设置多个域名的 Webhook 绑定"""
    if not body.domain_ids:
        return {"ok": True, "updated": 0}

    # 查出这些 ID 是否都归该用户所有
    result = await db.execute(
        select(Domain.id).where(Domain.id.in_(body.domain_ids), Domain.user_id == user.id)
    )
    valid_ids = [r for r, in result.all()]
    if not valid_ids:
        return {"ok": True, "updated": 0}

    # 验证 webhook 都属于当前用户
    if body.webhooks:
        wh_ids = [b.webhook_id for b in body.webhooks]
        owned = await db.execute(
            select(Webhook.id).where(Webhook.id.in_(wh_ids), Webhook.user_id == user.id)
        )
        owned_ids = {r for r, in owned.all()}
        for b in body.webhooks:
            if b.webhook_id not in owned_ids:
                raise HTTPException(status_code=400, detail=f"Webhook {b.webhook_id} 不存在")

    # 清除这些特定域名的旧绑定
    await db.execute(delete(DomainWebhook).where(DomainWebhook.domain_id.in_(valid_ids)))

    # 为所有合法域名写新绑定
    for d_id in valid_ids:
        for b in body.webhooks:
            db.add(DomainWebhook(
                domain_id=d_id,
                webhook_id=b.webhook_id,
                threshold_days=b.threshold_days,
                enabled=b.enabled,
            ))
            
    await db.commit()
    return {"ok": True, "updated": len(valid_ids)}
