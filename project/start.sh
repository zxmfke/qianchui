#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  千锤·营销话术AI操作系统 - 一键启动"
echo "============================================"
echo ""

# 选择 Python
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  PY="backend/venv/Scripts/python.exe"
else
  PY="backend/venv/bin/python"
fi

# Step 1: 初始化数据库
echo "[1/3] 检查数据库..."
if [ ! -f "backend/qianchui.db" ]; then
  echo "       初始化种子数据..."
  (cd backend && $PY seed_data.py)
  echo "       种子数据已导入。"
else
  echo "       数据库已存在。"
fi
echo ""

# Step 2: 启动后端
if netstat -ano 2>/dev/null | grep -q ":8001.*LISTEN"; then
  echo "[2/3] 后端已在运行 (8001)"
else
  echo "[2/3] 启动后端 API..."
  (cd backend && $PY -m uvicorn app.main:app --host 0.0.0.0 --port 8001) &
  sleep 3
  echo "       后端 PID: $!"
fi
echo ""

# Step 3: 启动前端
if netstat -ano 2>/dev/null | grep -q ":3000.*LISTEN"; then
  echo "[3/3] 前端已在运行 (3000)"
else
  echo "[3/3] 启动前端..."
  (cd frontend && npm run dev) &
  sleep 3
  echo "       前端 PID: $!"
fi

echo ""
echo "============================================"
echo "  全部就绪"
echo "============================================"
echo "  前端:     http://localhost:3000"
echo "  后端API:  http://localhost:8001"
echo "  API文档:  http://localhost:8001/docs"
echo ""
echo "  登录账号: demo"
echo "  登录密码: demo123456"
echo "============================================"
echo ""
echo "按 Ctrl+C 停止所有服务"
wait 2>/dev/null || true
