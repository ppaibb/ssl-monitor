module.exports = {
  apps: [
    {
      name: "ssl-monitor-backend",
      // 使用 venv 里的 uvicorn，也可换成系统路径
      script: "venv/bin/uvicorn",
      args: "main:app --host 127.0.0.1 --port 8000 --workers 1",
      cwd: "/data/ssl-monitor-scf/backend",
      interpreter: "none",
      watch: false,
      restart_delay: 3000,
      max_restarts: 10,
    },
  ],
};
