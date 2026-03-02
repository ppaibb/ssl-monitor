# SSL 证书监控平台

基于 **FastAPI + Vue 3 + SQLite** 的多用户 SSL 证书到期监控工具，支持 Webhook 告警推送、公开探针大屏与 Docker 一键部署。

## ✨ 功能一览

### 核心功能
- 🔒 **多用户隔离**：邮箱密码注册 / GitHub OAuth 登录，首位注册者自动成为管理员
- 🌐 **域名管理**：添加 / 编辑 / 删除域名，支持自定义**站点名称**、备注、端口
- 🔍 **实时检测**：手动单个检测 / 批量检测 / 全量检测，获取证书详细信息
- ⏰ **定时巡检**：每天北京时间 09:00 自动检测所有域名

### 标签与批量操作
- 🏷️ **项目标签**：为域名打标签分组，支持**标签联想 / 自动补全**
- ✅ **批量操作**：多选域名后批量检测、批量删除、批量配置告警

### 告警推送
- 🔔 **Webhook 告警**：支持企业微信、钉钉、自定义 Webhook
- ⚙️ **灵活配置**：全局告警 + 域名级独立告警

### 公开探针大屏 `/status`
- 📺 **无需登录**，只展示管理员的域名（适合挂在办公室大屏）
- 🔐 **域名脱敏**：每段仅保留首尾字符，防止信息泄露
- 🏷️ **标签筛选** + ⏱️ **到期筛选**（7 / 15 / 30 天）
- 🌙 **明暗主题**切换，60 秒自动刷新

## 🚀 快速部署（Docker）

```bash
# 一行命令即可完成部署
curl -fsSL https://raw.githubusercontent.com/ppaibb/ssl-monitor/main/install.sh | bash
```

或手动克隆后运行：

```bash
git clone https://github.com/ppaibb/ssl-monitor.git
cd ssl-monitor
bash install.sh
```

脚本会自动：创建 `/data/ssl-monitor/` 工作目录、生成 `.env`（含随机密钥）、`docker compose up -d --build`

> ✅ **需要 Docker 环境**。数据库持久化在 `/data/ssl-monitor/data/ssl_monitor.db`

## ⚙️ GitHub OAuth 配置（可选）

1. [创建 GitHub OAuth App](https://github.com/settings/developers)
   - Callback URL：`http://你的服务器IP/api/auth/github/callback`
2. 在 `backend/.env` 加入：
   ```
   GITHUB_CLIENT_ID=你的ClientID
   GITHUB_CLIENT_SECRET=你的ClientSecret
   FRONTEND_URL=http://你的服务器IP
   ```
3. 重启后端：`docker compose restart backend`

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, SQLAlchemy (Async), APScheduler |
| 存储 | SQLite (aiosqlite) |
| 前端 | Vue 3, TypeScript, Arco Design Vue, Vite |
| 部署 | Docker Compose + Nginx |

## 📁 项目结构

```
ssl-monitor/
├── backend/                 # FastAPI 后端
│   ├── main.py
│   ├── models.py            # ORM 模型
│   ├── schemas.py           # Pydantic Schema
│   ├── checker.py           # SSL 证书检测
│   ├── notifier.py          # Webhook 告警
│   ├── scheduler.py         # 定时任务
│   ├── routers/
│   │   ├── auth.py          # 登录 / 注册 / GitHub OAuth
│   │   ├── domains.py       # 域名 CRUD / 检测 / Webhook
│   │   ├── admin.py         # 管理员接口
│   │   └── public.py        # 公开探针（无需登录）
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api.ts
│   │   └── views/
│   │       ├── Login.vue
│   │       ├── Dashboard.vue
│   │       ├── Admin.vue
│   │       └── PublicStatus.vue
│   └── Dockerfile
│
├── docker-compose.yml       # 一键启动
├── install.sh               # 一键部署脚本
├── nginx.conf               # Nginx 参考配置
├── DEPLOY.md                # 详细部署指南
└── CHANGELOG.md             # 功能变更记录
```

## 📡 主要 API

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册 | ❌ |
| POST | `/api/auth/login` | 登录 | ❌ |
| GET | `/api/auth/github` | GitHub OAuth | ❌ |
| GET | `/api/domains` | 域名列表 | ✅ |
| POST | `/api/domains` | 添加域名 | ✅ |
| PUT | `/api/domains/{id}` | 编辑域名 | ✅ |
| GET | `/api/domains/check` | 全量检测 | ✅ |
| GET | `/api/domains/check-one` | 单个检测 | ✅ |
| POST | `/api/domains/check-batch` | 批量检测 | ✅ |
| GET | `/api/public/status` | 公开探针数据 | ❌ |

## 📄 License

MIT
