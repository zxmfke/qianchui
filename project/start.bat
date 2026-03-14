@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   千锤·营销话术AI操作系统 - 一键启动
echo ============================================
echo.

:: ── Step 1: 初始化数据库（如果为空） ──
echo [1/3] 检查数据库...
if not exist "backend\qianchui.db" (
    echo        数据库不存在，初始化种子数据...
    cd backend
    venv\Scripts\python.exe seed_data.py
    cd ..
    echo        种子数据已导入。
) else (
    echo        数据库已存在，跳过。
)
echo.

:: ── Step 2: 启动后端 ──
netstat -ano 2>nul | findstr ":8001.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [2/3] 后端已在运行 (8001)，跳过。
) else (
    echo [2/3] 启动后端 API ...
    start "千锤-后端" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
    echo        后端启动中... 等待 5 秒
    timeout /t 5 /nobreak >nul
)
echo.

:: ── Step 3: 启动前端 ──
netstat -ano 2>nul | findstr ":3000.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [3/3] 前端已在运行 (3000)，跳过。
) else (
    echo [3/3] 启动前端...
    start "千锤-前端" cmd /k "cd /d "%~dp0frontend" && npm run dev"
    echo        前端启动中... 等待 5 秒
    timeout /t 5 /nobreak >nul
)

echo.
echo ============================================
echo   全部就绪
echo ============================================
echo   前端:     http://localhost:3000
echo   后端API:  http://localhost:8001
echo   API文档:  http://localhost:8001/docs
echo.
echo   登录账号: demo
echo   登录密码: demo123456
echo ============================================
echo.
echo 按任意键关闭此窗口（服务继续在后台运行）
pause >nul
