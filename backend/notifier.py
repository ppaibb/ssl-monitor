import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


def _build_text(result: dict) -> str:
    domain = result["domain"]
    port = result["port"]
    label = f"{domain}" if port == 443 else f"{domain}:{port}"

    if result.get("error"):
        return f"【SSL 告警】{label} 检测失败\n错误：{result['error']}\n检测时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

    days = result["days_left"]
    not_after = result.get("not_after", "-")
    issuer = result.get("issuer_cn") or "-"

    if days <= 0:
        level = "🔴 已过期"
    elif days <= 7:
        level = f"🔴 紧急（剩 {days} 天）"
    elif days <= 14:
        level = f"🟠 警告（剩 {days} 天）"
    else:
        level = f"🟡 提醒（剩 {days} 天）"

    return (
        f"【SSL 告警】{label}\n"
        f"状态：{level}\n"
        f"到期时间：{not_after}\n"
        f"颁发机构：{issuer}\n"
        f"检测时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )


async def send_webhook(webhook, result: dict) -> tuple[bool, str | None]:
    """发送单条告警，返回 (ok, error_msg)"""
    text = _build_text(result)
    url: str = webhook.url
    wtype: str = webhook.type

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if wtype == "wecom":
                payload = {"msgtype": "text", "text": {"content": text}}
                r = await client.post(url, json=payload)
            elif wtype == "dingtalk":
                payload = {
                    "msgtype": "text",
                    "text": {"content": text},
                    "at": {"isAtAll": False},
                }
                r = await client.post(url, json=payload)
            else:  # custom
                domain = result["domain"]
                port = result["port"]
                payload = {
                    "title": f"SSL 告警：{domain}" if port == 443 else f"SSL 告警：{domain}:{port}",
                    "content": text,
                    "domain": domain,
                    "port": port,
                    "days_left": result.get("days_left"),
                    "not_after": result.get("not_after"),
                    "is_expired": result.get("is_expired", False),
                    "is_expiring_soon": result.get("is_expiring_soon", False),
                    "error": result.get("error"),
                }
                r = await client.post(url, json=payload)

        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, None

    except Exception as e:
        return False, str(e)


async def notify_user_results(webhooks: list, results: list[dict]):
    """全局模式：对一个用户的所有检测结果，遍历 webhooks 发送需要告警的域名"""
    if not webhooks or not results:
        return

    for wh in webhooks:
        if not wh.enabled:
            continue
        for res in results:
            days = res.get("days_left")
            needs_alert = (
                res.get("error")
                or res.get("is_expired")
                or (days is not None and days <= wh.threshold_days)
            )
            if not needs_alert:
                continue
            ok, err = await send_webhook(wh, res)
            if not ok:
                logger.warning(f"Webhook [{wh.name}] 发送失败：{err}")
            else:
                logger.info(f"Webhook [{wh.name}] 告警已发送：{res['domain']}")


async def notify_single(domain_webhooks: list, global_webhooks: list, result: dict):
    """
    域名级模式：
    - 如果该域名有绑定记录，只用域名级绑定（可覆盖阈值）
    - 否则回退到全局 webhooks
    domain_webhooks: list of (DomainWebhook ORM 对象, Webhook ORM 对象)
    global_webhooks: list of Webhook ORM 对象
    """
    if domain_webhooks:
        for dw, wh in domain_webhooks:
            if not dw.enabled or not wh.enabled:
                continue
            threshold = dw.threshold_days if dw.threshold_days is not None else wh.threshold_days
            days = result.get("days_left")
            needs = result.get("error") or result.get("is_expired") or (days is not None and days <= threshold)
            if not needs:
                continue
            ok, err = await send_webhook(wh, result)
            if not ok:
                logger.warning(f"Webhook [{wh.name}] (域名级) 发送失败：{err}")
            else:
                logger.info(f"Webhook [{wh.name}] (域名级) 告警已发送：{result['domain']}")
    else:
        # 回退全局
        await notify_user_results(global_webhooks, [result])
