# 部署指南

## 新版（Python + FastAPI）部署

### 1. 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env 填入 SECRET_KEY、FRONTEND_URL 等

# 开发
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产（PM2）
cd ..
pm2 start ecosystem.config.js
pm2 save && pm2 startup
```

### 2. 前端

```bash
cd frontend-v2
npm install
npm run dev        # 开发，访问 http://localhost:5173
npm run build      # 构建到 dist/
```

### 3. Nginx

```bash
# 修改 nginx.conf 中的 server_name 和 SSL 证书路径
sudo cp nginx.conf /etc/nginx/sites-available/ssl-monitor
sudo ln -s /etc/nginx/sites-available/ssl-monitor /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Cloudflare Workers 版本部署

### 依赖

- [Cloudflare](https://dash.cloudflare.com) 账号
- Node.js + `npx wrangler`

---

## 第一步：创建 KV 命名空间

```bash
cd cloudflare-worker
npx wrangler kv:namespace create KV
```

将返回的 `id` 填入 `wrangler.toml`：

```toml
[[kv_namespaces]]
binding = "KV"
id     = "你的 KV namespace id"
```

---

## 第二步：配置 GitHub OAuth（可选）

1. 在 [GitHub Developer Settings](https://github.com/settings/developers) 创建 OAuth App
   - Callback URL：`https://<your-worker>.workers.dev/api/auth/github/callback`
2. 将 Client ID 写入 `wrangler.toml` `[vars]`：
   ```toml
   GITHUB_CLIENT_ID = "你的 Client ID"
   FRONTEND_URL     = "https://你的前端域名"
   ```
3. 加密存储 Client Secret：
   ```bash
   npx wrangler secret put GITHUB_CLIENT_SECRET
   ```

---

## 第三步：部署 Worker

```bash
cd cloudflare-worker
npx wrangler deploy
```

---

## 第四步：部署前端

```bash
npx wrangler pages deploy ../frontend --project-name ssl-monitor-frontend
```

---

## 环境变量一览

| 变量 | 存放位置 | 说明 |
|------|----------|------|
| `GITHUB_CLIENT_ID` | `wrangler.toml [vars]` | GitHub OAuth App Client ID |
| `FRONTEND_URL` | `wrangler.toml [vars]` | 前端页面地址，用于 OAuth 回调跳转 |
| `ADMIN_EMAIL` | `wrangler.toml [vars]` | 可选，指定管理员邮箱 |
| `GITHUB_CLIENT_SECRET` | `wrangler secret` | GitHub OAuth 密钥（加密存储）|

---

## 定时检测

Worker 默认每天 **02:00 UTC（北京时间 10:00）** 自动检测所有用户的域名，结果写入 KV 缓存。

修改频率：编辑 `wrangler.toml` 中的 `crons` 字段后重新 `wrangler deploy`。


---

## 第一步：本地测试

```bash
pip install cos-python-sdk-v5

# 编辑 local_test.py 中的域名和 Webhook 后运行
python local_test.py
```

---

## 第二步：创建 COS Bucket（存放域名列表）

1. 登录[腾讯云 COS 控制台](https://console.cloud.tencent.com/cos)
2. 创建 Bucket，例如 `ssl-monitor-config-123456`（私有读写）
3. 上传 `domains.json` 到 Bucket 根目录
4. 记下 **Bucket 名称** 和 **所在地域**（如 `ap-guangzhou`）

---

## 第三步：创建云函数

1. 进入[腾讯云 SCF 控制台](https://console.cloud.tencent.com/scf)
2. 新建函数：
   - **函数类型**：事件函数
   - **运行环境**：Python 3.9
   - **创建方式**：本地上传 ZIP 包
   - **执行方法**：`index.main_handler`
   - **超时时间**：60 秒（域名多时适当加大）
   - **内存**：128 MB

3. 打包上传（排除 `local_test.py`）：
   ```powershell
   # Windows PowerShell
   Compress-Archive -Path index.py, cert_checker.py, notifier.py, cos_storage.py -DestinationPath deploy.zip
   ```

---

## 第四步：配置环境变量

在 SCF 控制台 → 函数配置 → 环境变量中添加：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `WEBHOOK_URL` | `https://你的webhook地址` | 自定义 Webhook URL |
| `COS_BUCKET` | `ssl-monitor-config-123456` | COS Bucket 名称 |
| `COS_REGION` | `ap-guangzhou` | COS 所在地域 |

> 如果不用 COS，可以直接设置 `DOMAINS` 变量（逗号分隔）：
> `DOMAINS = example.com,api.example.com,internal.corp:8443`

---

## 第五步：配置函数角色权限（使用 COS 时必须）

1. SCF 控制台 → 函数配置 → **执行角色**
2. 点击角色名进入 CAM 控制台
3. 为该角色添加策略：`QcloudCOSReadOnlyAccess`

---

## 第六步：设置定时触发器

1. SCF 控制台 → 触发管理 → 创建触发器
2. 选择 **定时触发器**
3. 配置 Cron 表达式：

| 频率 | Cron 表达式 |
|------|------------|
| 每天早上 9:00 | `0 0 9 * * * *` |
| 每天两次（9:00 和 21:00）| `0 0 9,21 * * * *` |
| 每 6 小时 | `0 0 */6 * * * *` |

---

## Webhook Payload 格式

你的 Webhook 将收到如下 JSON：

```json
{
  "title": "🔴 SSL证书7天内到期：example.com",
  "content": "域名：example.com\n剩余天数：6 天\n到期时间：2026-03-05 12:00:00 UTC\n颁发机构：Let's Encrypt\n紧急程度：紧急\n检测时间：2026-02-27 09:00:00 UTC",
  "level": "紧急",
  "domain": "example.com",
  "days_left": 6,
  "alert_level": 7,
  "raw": { ... }
}
```

---

## 更新域名列表

只需修改 COS 上的 `domains.json` 文件即可，无需重新部署函数。

```json
[
  { "domain": "example.com",     "port": 443,  "note": "主站" },
  { "domain": "api.example.com", "port": 443,  "note": "API" },
  { "domain": "internal.corp",   "port": 8443, "note": "内部" }
]
```
