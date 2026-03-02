#!/bin/bash
set -e

# ===========================
# SSL Monitor 一键部署脚本
# 使用方式：登录服务器后执行
# bash install.sh
# ===========================

WORK_DIR="/data/ssl-monitor"
REPO_URL="https://github.com/ppaibb/ssl-monitor.git"

echo "========================================="
echo "  SSL Monitor 一键部署"
echo "========================================="

# 1. 创建工作目录
echo "[1/5] 创建工作目录 ${WORK_DIR} ..."
mkdir -p ${WORK_DIR}
cd ${WORK_DIR}

# 2. 拉取代码
if [ -d ".git" ]; then
    echo "[2/5] 检测到已有仓库，拉取最新代码..."
    git pull origin main
else
    echo "[2/5] 克隆仓库..."
    git clone ${REPO_URL} .
fi

# 3. 创建数据持久化目录
echo "[3/5] 创建数据目录..."
mkdir -p ${WORK_DIR}/data

# 4. 生成 .env（如果不存在）
if [ ! -f "${WORK_DIR}/backend/.env" ]; then
    echo "[4/5] 生成后端 .env 配置..."
    SECRET=$(openssl rand -hex 32)
    cat > ${WORK_DIR}/backend/.env <<EOF
SECRET_KEY=${SECRET}
DATABASE_URL=sqlite+aiosqlite:///./data/ssl_monitor.db
FRONTEND_URL=http://$(hostname -I | awk '{print $1}')
EOF
    echo "  -> SECRET_KEY 已自动生成"
    echo "  -> .env 文件位于 ${WORK_DIR}/backend/.env"
else
    echo "[4/5] .env 已存在，跳过"
fi

# 5. Docker Compose 构建并启动
echo "[5/5] 构建并启动 Docker 容器..."
docker compose up -d --build

echo ""
echo "========================================="
echo "  ✅ 部署完成！"
echo "========================================="
echo ""
echo "  前端地址:  http://$(hostname -I | awk '{print $1}')"
echo "  后端 API:  http://$(hostname -I | awk '{print $1}')/api"
echo "  探针大屏:  http://$(hostname -I | awk '{print $1}')/status"
echo ""
echo "  工作目录:  ${WORK_DIR}"
echo "  数据目录:  ${WORK_DIR}/data/"
echo "  数据库:    ${WORK_DIR}/data/ssl_monitor.db"
echo ""
echo "  常用命令："
echo "    查看日志:  cd ${WORK_DIR} && docker compose logs -f"
echo "    重启服务:  cd ${WORK_DIR} && docker compose restart"
echo "    停止服务:  cd ${WORK_DIR} && docker compose down"
echo "    更新部署:  cd ${WORK_DIR} && git pull && docker compose up -d --build"
echo ""
echo "  ⚠️ 首个注册的用户自动成为管理员"
echo "========================================="
