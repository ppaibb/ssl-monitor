# SSL 证书监控平台

基于 **FastAPI + Vue 3 + SQLite** 的多用户 SSL 证书到期监控工具，支持 Webhook 告警推送与公开探针大屏。

## ✨ 功能一览

### 核心功能
- 🔒 **多用户隔离**：邮箱密码注册 / GitHub OAuth 登录，首位注册者自动成为管理员
- 🌐 **域名管理**：添加 / 编辑 / 删除域名，支持自定义站点名称、备注、端口
- 🔍 **实时检测**：手动单个检测 / 批量检测 / 全量检测，获取证书详细信息（到期时间、颁发机构、SAN 列表等）
- ⏰ **定时巡检**：每天自动检测所有域名证书到期时间

### 标签与批量操作
- 🏷️ **项目标签**：为域名打标签分组（如"生产环境"、"CDN"），支持标签联想/自动补全
- ✅ **批量操作**：多选域名后可批量检测、批量删除、批量配置告警

### 告警推送
- 🔔 **Webhook 告警**：支持企业微信、钉钉、自定义 Webhook
- ⚙️ **灵活配置**：全局告警 + 域名级独立告警，可设置不同的到期阈值

### 公开探针大屏 `/status`
- 📺 **无需登录**即可访问的监控大屏，适合挂在办公室电视上
- 🔐 **域名脱敏**：自动隐藏域名敏感信息（每段只保留首尾字符）
- 🏷️ **标签筛选**：按项目标签快速过滤
- ⏱️ **到期筛选**：一键查看 7天 / 15天 / 30天 内到期的站点
- 🌙 **明暗主题**：支持亮色/暗色切换，60秒自动刷新

### 管理后台
- 👥 **管理员面板**：查看所有用户的域名与检测结果

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, SQLAlchemy (Async), APScheduler |
| 存储 | SQLite (aiosqlite) |
| 前端 | Vue 3, TypeScript, Arco Design Vue, Vite |
| 部署 | Uvicorn + PM2 + Nginx |

## 📁 项目结构

```
ssl-monitor/
├── backend/
│   ├── main.py              # FastAPI 应用入口，路由注册 & CORS
│   ├── models.py            # SQLAlchemy ORM 模型 (User, Domain, CertResult, Webhook...)
│   ├── schemas.py           # Pydantic 请求/响应 Schema
│   ├── database.py          # 异步数据库连接
│   ├── config.py            # 环境变量配置
│   ├── checker.py           # SSL 证书检测核心逻辑
│   ├── notifier.py          # Webhook 告警推送
│   ├── scheduler.py         # APScheduler 定时任务
│   ├── auth_utils.py        # JWT 认证工具
│   ├── routers/
│   │   ├── auth.py          # 登录 / 注册 / OAuth
│   │   ├── domains.py       # 域名 CRUD / 检测 / 批量操作 / Webhook 配置
│   │   ├── admin.py         # 管理员接口
│   │   └── public.py        # 公开探针接口（无需登录）
│   ├── requirements.txt
│   ├── .env.example
│   └── ssl_monitor.db       # SQLite 数据库文件
│
├── frontend-v2/
│   ├── src/
│   │   ├── api.ts           # Axios API 封装 & TypeScript 类型
│   │   ├── views/
│   │   │   ├── Login.vue    # 登录页
│   │   │   ├── Dashboard.vue # 主控面板（域名卡片 / 批量操作 / Webhook 管理）
│   │   │   ├── Admin.vue    # 管理员面板
│   │   │   └── PublicStatus.vue # 公开探针大屏
│   │   ├── router/index.ts  # Vue Router 路由配置
│   │   └── store/user.ts    # Pinia 用户状态管理
│   ├── package.json
│   └── vite.config.ts       # Vite 配置（含 API 代理）
│
├── README.md                # 本文件
├── DEPLOY.md                # 部署指南
├── MIGRATION.md             # 数据库迁移说明
├── nginx.conf               # Nginx 参考配置
└── ecosystem.config.js      # PM2 部署配置
```

## 🚀 快速开始

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # 编辑 .env 填入 SECRET_KEY 等
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend-v2
npm install
npm run dev                   # 开发模式，访问 http://localhost:5173
```

### 生产部署

详见 [DEPLOY.md](./DEPLOY.md)。

## 📡 API 端点概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册 | ❌ |
| POST | `/api/auth/login` | 登录 | ❌ |
| GET | `/api/domains` | 获取域名列表 | ✅ |
| POST | `/api/domains` | 添加域名 | ✅ |
| PUT | `/api/domains/{id}` | 编辑域名 | ✅ |
| DELETE | `/api/domains` | 删除域名 | ✅ |
| GET | `/api/domains/check` | 全量检测 | ✅ |
| GET | `/api/domains/check-one` | 单个检测 | ✅ |
| POST | `/api/domains/check-batch` | 批量检测 | ✅ |
| DELETE | `/api/domains/batch` | 批量删除 | ✅ |
| PUT | `/api/domains/{id}/webhooks` | 配置域名告警 | ✅ |
| GET | `/api/public/status` | 公开探针数据 | ❌ |

## 📄 License

MIT
