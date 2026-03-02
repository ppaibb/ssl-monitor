import logging
import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Domain, CertResult, User
from schemas import PublicStatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/status", tags=["Public"])

def mask_domain(domain: str) -> str:
    """对域名的每一段都做脱敏，只保留 TLD 原样。
    例如: agent.zfshoufutong.com -> a***t.z*********g.com
    """
    parts = domain.split('.')
    if len(parts) < 2:
        return "[masked]"
    
    # 最后一段是 TLD (.com, .cn 等)，保持原样
    # 如果倒数第二段是常见的二级 TLD（如 .com.cn, .edu.cn），也保留
    tld_parts = 1
    common_second_tlds = {'com', 'net', 'org', 'edu', 'gov', 'co'}
    if len(parts) >= 3 and parts[-2] in common_second_tlds:
        tld_parts = 2
    
    def mask_part(s: str) -> str:
        if len(s) <= 2:
            return s[0] + '*'
        return s[0] + '*' * (len(s) - 2) + s[-1]
    
    masked = [mask_part(p) for p in parts[:-tld_parts]]
    masked.extend(parts[-tld_parts:])
    return '.'.join(masked)

@router.get("", response_model=list[PublicStatusOut])
async def get_public_status(db: AsyncSession = Depends(get_db)):
    """
    Get all domains and their most recent check results.
    The domain string will be masked for public viewing.
    """
    # 只展示管理员用户的域名
    admin_result = await db.execute(select(User).where(User.is_admin == True))
    admin_ids = [u.id for u in admin_result.scalars().all()]
    
    domain_result = await db.execute(select(Domain).where(Domain.user_id.in_(admin_ids)))
    domains = domain_result.scalars().all()
    
    public_stats = []
    
    cert_result_res = await db.execute(
        select(CertResult).where(CertResult.user_id.in_(admin_ids))
    )
    results = cert_result_res.scalars().all()
    
    # Group results by domain and port to find the latest
    latest_results = {}
    for r in results:
        key = (r.domain, r.port)
        # Assuming the ID increments or checked_at is later
        if key not in latest_results or r.checked_at > latest_results[key].checked_at:
            latest_results[key] = r
            
    # Deduplicate domains across users
    unique_domains = {(d.domain, d.port): d for d in domains}
            
    for key, d in unique_domains.items():
        result = latest_results.get(key)
        if result:
            # 解析 tags JSON
            try:
                tags = json.loads(d.tags) if d.tags else []
            except (ValueError, TypeError):
                tags = []
            public_stats.append(PublicStatusOut(
                name=d.name,
                masked_domain=mask_domain(d.domain),
                port=d.port,
                days_left=result.days_left,
                is_expired=result.is_expired,
                is_expiring_soon=result.is_expiring_soon,
                error=result.error,
                checked_at=result.checked_at,
                tags=tags
            ))
            
    return public_stats
