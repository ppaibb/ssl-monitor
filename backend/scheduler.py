import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete

from checker import check_certs_concurrent, serialize_san, deserialize_san
from config import get_settings
from database import AsyncSessionLocal
from models import Domain, CertResult, Webhook, DomainWebhook
from notifier import notify_single

logger = logging.getLogger(__name__)
settings = get_settings()
scheduler = AsyncIOScheduler()


async def daily_check_all():
    logger.info("开始每日证书检测...")
    async with AsyncSessionLocal() as db:
        domains_result = await db.execute(select(Domain))
        domains = domains_result.scalars().all()

        targets = list({(d.domain, d.port) for d in domains})
        if not targets:
            logger.info("没有域名需要检测")
            return

        results = await check_certs_concurrent(targets)

        domain_users: dict[tuple, list[int]] = {}
        for d in domains:
            key = (d.domain, d.port)
            domain_users.setdefault(key, []).append(d.user_id)

        now = datetime.utcnow()
        for res in results:
            key = (res["domain"], res["port"])
            for user_id in domain_users.get(key, []):
                cr = CertResult(
                    user_id=user_id,
                    checked_at=now,
                    san=serialize_san(res.get("san")),
                    **{k: v for k, v in res.items() if k != "san"},
                )
                db.add(cr)

        await db.flush()
        # 保留最近 60 条历史
        for res in results:
            key = (res["domain"], res["port"])
            for user_id in domain_users.get(key, []):
                subq = (
                    select(CertResult.id)
                    .where(CertResult.user_id == user_id, CertResult.domain == res["domain"], CertResult.port == res["port"])
                    .order_by(CertResult.checked_at.desc())
                    .offset(60)
                )
                await db.execute(delete(CertResult).where(CertResult.id.in_(subq)))

        await db.commit()

        # 按用户发送 Webhook 告警（域名级优先，否则回退全局）
        for d in domains:
            key = (d.domain, d.port)
            res = next((r for r in results if r["domain"] == d.domain and r["port"] == d.port), None)
            if not res:
                continue

            # 查域名级绑定
            dw_result = await db.execute(
                select(DomainWebhook, Webhook)
                .join(Webhook, DomainWebhook.webhook_id == Webhook.id)
                .where(DomainWebhook.domain_id == d.id)
            )
            domain_whs = dw_result.all()  # list of (DomainWebhook, Webhook)

            # 全局 webhooks（回退用）
            global_wh_result = await db.execute(
                select(Webhook).where(Webhook.user_id == d.user_id, Webhook.enabled == True)
            )
            global_whs = global_wh_result.scalars().all()

            await notify_single(domain_whs, global_whs, res)

        logger.info(f"每日检测完成，共 {len(results)} 个域名")


def start_scheduler():
    scheduler.add_job(
        daily_check_all,
        "cron",
        hour=settings.DAILY_CHECK_HOUR,
        minute=0,
        id="daily_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"定时任务已启动，每天 UTC {settings.DAILY_CHECK_HOUR}:00 执行检测")
