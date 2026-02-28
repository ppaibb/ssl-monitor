from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import require_admin
from checker import check_certs_concurrent, serialize_san
from database import get_db
from models import User, Domain, CertResult
from schemas import AdminUserOut, DomainOut, CertResultOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()

    out = []
    for u in users:
        count_result = await db.execute(
            select(func.count()).select_from(Domain).where(Domain.user_id == u.id)
        )
        domain_count = count_result.scalar()
        out.append({**u.__dict__, "domain_count": domain_count})
    return out


@router.get("/domains", response_model=list[DomainOut])
async def list_all_domains(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Domain))
    return result.scalars().all()


@router.post("/check-all")
async def check_all(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    domains_result = await db.execute(select(Domain))
    domains = domains_result.scalars().all()

    targets = list({(d.domain, d.port) for d in domains})
    if not targets:
        return {"checked": 0}

    results = await check_certs_concurrent(targets)

    now = datetime.utcnow()
    # 构建 domain -> user_id 映射
    domain_users: dict[tuple, list[int]] = {}
    for d in domains:
        key = (d.domain, d.port)
        domain_users.setdefault(key, []).append(d.user_id)

    for res in results:
        key = (res["domain"], res["port"])
        for user_id in domain_users.get(key, []):
            await db.execute(
                delete(CertResult).where(
                    CertResult.user_id == user_id,
                    CertResult.domain == res["domain"],
                    CertResult.port == res["port"],
                )
            )
            cr = CertResult(
                user_id=user_id,
                checked_at=now,
                san=serialize_san(res.get("san")),
                **{k: v for k, v in res.items() if k != "san"},
            )
            db.add(cr)

    await db.commit()
    return {"checked": len(results)}
