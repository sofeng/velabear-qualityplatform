@echo off
chcp 65001 >nul
echo ====================================
echo 前端服务诊断工具
echo ====================================
echo.

echo [1] 检查3000端口状态...
netstat -ano | findstr :3000
if errorlevel 1 (
    echo    ❌ 3000端口未监听
) else (
    echo    ✅ 3000端口正在监听
)
echo.

echo [2] 检查Node进程...
tasklist | findstr node
if errorlevel 1 (
    echo    ❌ Node进程未运行
) else (
    echo    ✅ Node进程正在运行
)
echo.

echo [3] 测试HTTP连接 (localhost:3000)...
curl -I http://localhost:3000 2>nul | findstr "HTTP"
if errorlevel 1 (
    echo    ❌ 无法连接到localhost:3000
) else (
    echo    ✅ localhost:3000 响应正常
)
echo.

echo [4] 测试HTTP连接 (127.0.0.1:3000)...
curl -I http://127.0.0.1:3000 2>nul | findstr "HTTP"
if errorlevel 1 (
    echo    ❌ 无法连接到127.0.0.1:3000
) else (
    echo    ✅ 127.0.0.1:3000 响应正常
)
echo.

echo [5] 本机IP地址...
ipconfig | findstr IPv4
echo.

echo [6] 检查Django后端 (8000端口)...
netstat -ano | findstr :8000
if errorlevel 1 (
    echo    ⚠️  Django后端未运行
) else (
    echo    ✅ Django后端正在运行
)
echo.

echo ====================================
echo 诊断结果
echo ====================================
echo.

netstat -ano | findstr :3000 >nul
if errorlevel 1 (
    echo ❌ 前端服务未启动
    echo.
    echo 请运行以下命令启动前端:
    echo   cd D:\AI\syswin-testhub\testhub-platform-src\frontend
    echo   npm run dev
) else (
    echo ✅ 前端服务已启动
    echo.
    echo 请在浏览器访问以下地址:
    echo.
    echo   主要地址: http://localhost:3000
    echo   备用地址: http://127.0.0.1:3000
    echo.
    echo 如果浏览器无法访问，请尝试:
    echo   1. 按 Ctrl+Shift+Delete 清除浏览器缓存
    echo   2. 按 Ctrl+F5 强制刷新页面
    echo   3. 使用隐私/无痕模式访问
    echo   4. 更换浏览器尝试
)

echo.
echo ====================================
pause
