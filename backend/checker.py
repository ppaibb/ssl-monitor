import asyncio
import json
import socket
import ssl
from datetime import datetime

from config import get_settings

settings = get_settings()


def _check_cert_sync(domain: str, port: int, timeout: int) -> dict:
    ctx = ssl.create_default_context()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.settimeout(timeout)
    try:
        with ctx.wrap_socket(raw_sock, server_hostname=domain) as s:
            s.connect((domain, port))
            cert = s.getpeercert()
    finally:
        raw_sock.close()

    not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days_left = (not_after - datetime.utcnow()).days
    san = [v for _, v in cert.get("subjectAltName", [])]
    issuer = dict(x[0] for x in cert["issuer"])
    subject = dict(x[0] for x in cert["subject"])

    return {
        "domain": domain,
        "port": port,
        "days_left": days_left,
        "not_after": not_after.date().isoformat(),
        "issuer_cn": issuer.get("commonName", ""),
        "issuer_org": issuer.get("organizationName", ""),
        "subject_cn": subject.get("commonName", ""),
        "san": san,
        "is_expired": days_left <= 0,
        "is_expiring_soon": 0 < days_left <= 30,
        "error": None,
    }


async def check_cert(domain: str, port: int = 443) -> dict:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None, _check_cert_sync, domain, port, settings.CHECK_TIMEOUT
        )
    except Exception as e:
        return {
            "domain": domain,
            "port": port,
            "days_left": None,
            "not_after": None,
            "issuer_cn": None,
            "issuer_org": None,
            "subject_cn": None,
            "san": None,
            "is_expired": False,
            "is_expiring_soon": False,
            "error": str(e),
        }


async def check_certs_concurrent(targets: list[tuple[str, int]], max_concurrency: int = 20) -> list[dict]:
    sem = asyncio.Semaphore(max_concurrency)

    async def bounded(domain, port):
        async with sem:
            return await check_cert(domain, port)

    tasks = [bounded(d, p) for d, p in targets]
    return await asyncio.gather(*tasks)


def serialize_san(san: list[str] | None) -> str | None:
    if san is None:
        return None
    return json.dumps(san)


def deserialize_san(san_str: str | None) -> list[str] | None:
    if san_str is None:
        return None
    try:
        return json.loads(san_str)
    except Exception:
        return []
