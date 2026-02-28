# 重构计划：迁移到 Python FastAPI + Vue 3

## 为什么重构

Cloudflare Workers 沙箱无法直连获取 TLS 证书，必须依赖 crt.sh / CertSpotter 等第三方 CT 日志 API，存在以下问题：
- 内网域名、私有 CA 证书无法检测
- 第三方 API 不稳定，大域名超时
- 新证书同步到 CT 日志有延迟

迁移到自有服务器后用 Python `ssl` 标准库直连，彻底解决上述问题。

---

## 目标技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI + Uvicorn |
| 证书检测 | `ssl` + `socket` 标准库（直连） |
| 数据库 | SQLite（SQLAlchemy ORM） |
| 认证 | bcrypt 密码哈希 + token（存 DB） |
| 定时任务 | APScheduler |
| 进程管理 | PM2 或 systemd |
| 反向代理 | Nginx |
| 前端 | Vue 3 + Vite + Arco Design |

---

## 后端 API 设计（沿用现有接口）

```
POST  /api/auth/register
POST  /api/auth/login
POST  /api/auth/logout
GET   /api/auth/me
POST  /api/auth/change-password
GET   /api/auth/github          (GitHub OAuth 可选)
GET   /api/auth/github/callback

GET    /api/domains
POST   /api/domains
DELETE /api/domains

GET   /api/check                (立即检测当前用户)
GET   /api/results              (获取缓存结果)

GET   /api/admin/users
GET   /api/admin/domains
POST  /api/admin/check-all
```

---

## 数据库表设计

```sql
users        (id, email, password_hash, is_admin, auth_method, github_id, created_at)
domains      (id, user_id, domain, port, note, added_at)
cert_results (id, user_id, domain, port, days_left, not_after, issuer, is_expired,
              is_expiring_soon, error, checked_at)
sessions     (token, user_id, expires_at)
```

---

## 证书检测核心代码（直连）

```python
import ssl, socket
from datetime import datetime

def check_cert(domain: str, port: int = 443) -> dict:
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
        s.settimeout(10)
        s.connect((domain, port))
        cert = s.getpeercert()
    
    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    days_left = (not_after - datetime.utcnow()).days
    san = [v for _, v in cert.get('subjectAltName', [])]
    issuer = dict(x[0] for x in cert['issuer'])
    
    return {
        'domain': domain, 'port': port,
        'days_left': days_left,
        'not_after': not_after.date().isoformat(),
        'issuer_cn': issuer.get('commonName', ''),
        'san': san,
        'is_expired': days_left <= 0,
        'is_expiring_soon': 0 < days_left <= 30,
    }
```

---

## 保留的 TODO（Cloudflare 版未完成）

- [ ] Webhook 告警通知（证书到期自动推送企业微信 / 钉钉 / 自定义）
- [ ] 登录频率限制（防暴力破解）
- [ ] 密码重置流程
- [ ] crt.sh / CertSpotter fallback（新版直连后可选保留用于历史数据补充）

---

## 服务器准备清单

```bash
# 安装 Node.js（前端构建用）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# 安装 Python 3.11+
sudo apt install -y python3 python3-pip python3-venv

# 安装 Nginx
sudo apt install -y nginx

# 安装 PM2
npm install -g pm2
```

---

## 前端重构要点

- 框架：Vue 3 + Vite + **Arco Design**
- 构建产物由 Nginx 直接 serve（替换 Cloudflare Pages）
- `DEFAULT_API` 改为服务器地址
- 登录页、仪表盘、管理员面板全部用 Arco 组件重写
- 证书详情弹窗、到期趋势图（用 Arco 内置图表）
