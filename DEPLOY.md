# 部署指南

## 环境要求

| 组件 | 最低版本 |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| Nginx | 1.18+（生产环境） |
| PM2 | 5+（生产环境，可选） |

---

## 一、后端部署

### 1. 安装依赖

```bash
cd backend
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | JWT 签名密钥，务必修改 | `my-super-secret-key-change-me` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///./ssl_monitor.db` |
| `FRONTEND_URL` | 前端地址（CORS 用） | `http://localhost:5173` |
| `GITHUB_CLIENT_ID` | GitHub OAuth（可选） | - |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth（可选） | - |

### 3. 启动后端

```bash
# 开发模式（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式（PM2 托管）
cd ..
pm2 start ecosystem.config.js
pm2 save && pm2 startup
```

> 首次启动时数据库会自动创建。**第一个注册的用户自动成为管理员。**

---

## 二、前端部署

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
# 访问 http://localhost:5173
# API 请求会自动代理到 http://localhost:8000
```

### 3. 生产构建

```bash
npm run build
# 产物在 dist/ 目录，由 Nginx 托管
```

---

## 三、Nginx 配置（生产环境）

项目根目录提供了 `nginx.conf` 参考配置，修改其中的域名和 SSL 证书路径后使用：

```bash
# 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/ssl-monitor
sudo ln -s /etc/nginx/sites-available/ssl-monitor /etc/nginx/sites-enabled/

# 测试并重载
sudo nginx -t && sudo systemctl reload nginx
```

Nginx 主要做两件事：
1. **静态文件**：将 `/` 指向前端 `dist/` 目录
2. **API 代理**：将 `/api` 请求转发到后端 `http://127.0.0.1:8000`

---

## 四、PM2 进程管理（生产环境）

项目提供了 `ecosystem.config.js`，使用 PM2 可以实现后端进程守护和自动重启：

```bash
# 安装 PM2（如果没有）
npm install -g pm2

# 启动
pm2 start ecosystem.config.js

# 查看状态
pm2 status

# 设置开机自启
pm2 save && pm2 startup
```

---

## 五、完整部署流程（快速版）

```bash
# 1. 克隆项目
git clone https://github.com/ppaibb/ssl-monitor.git
cd ssl-monitor

# 2. 后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # 编辑 .env 填入 SECRET_KEY
uvicorn main:app --host 0.0.0.0 --port 8000 &

# 3. 前端
cd ../frontend-v2
npm install && npm run build

# 4. Nginx + PM2（生产环境）
cd ..
sudo cp nginx.conf /etc/nginx/sites-available/ssl-monitor
sudo ln -s /etc/nginx/sites-available/ssl-monitor /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
pm2 start ecosystem.config.js && pm2 save
```

---

## 常见问题

### Q: 数据库在哪？
SQLite 数据库文件位于 `backend/ssl_monitor.db`，首次启动自动创建。

### Q: 如何备份数据？
直接复制 `ssl_monitor.db` 文件即可，建议定期备份。

### Q: 忘记密码怎么办？
目前没有密码重置功能，可以直接操作 SQLite 数据库修改：
```bash
cd backend
python -c "
import sqlite3, hashlib
conn = sqlite3.connect('ssl_monitor.db')
new_pwd = hashlib.sha256('新密码'.encode()).hexdigest()
conn.execute('UPDATE users SET hashed_password=? WHERE email=?', (new_pwd, '你的邮箱'))
conn.commit()
"
```

### Q: 定时检测的频率是多少？
默认每天 UTC 01:00（北京时间 09:00）自动检测一次，可在 `scheduler.py` 中修改。
