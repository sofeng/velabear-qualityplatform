@echo off
chcp 65001 >nul
setlocal

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

echo ============================================================
echo   AIDevTestOps development startup
echo ============================================================
echo.

echo [1/4] Starting Local Playwright recording agent...
call "%REPO_ROOT%\tools\start_local_playwright_agent.bat"
if errorlevel 1 (
    echo Local Playwright recording agent failed to start.
    pause
    exit /b 1
)

echo [2/4] Starting Django backend service (port 8000)...
start "Django Backend" /D "%REPO_ROOT%" cmd /k "python manage.py runserver"

timeout /t 3 >nul

echo [3/4] Starting frontend dev server (port 3000)...
start "Frontend Dev Server" /D "%REPO_ROOT%\frontend" cmd /k "npm run dev"

echo [4/4] Waiting for services...
timeout /t 8 >nul

echo.
echo ============================================================
echo   Services started
echo ============================================================
echo.
echo   Frontend:        http://localhost:3000
echo   Backend:         http://localhost:8000
echo   API docs:        http://localhost:8000/api/docs/
echo   Recording Agent: http://127.0.0.1:18765/health
echo.
echo ============================================================
echo.

choice /C YN /M "Open frontend in browser"

if errorlevel 2 goto :skip_browser
if errorlevel 1 goto :open_browser

:open_browser
echo Opening browser...
start http://localhost:3000
goto :end

:skip_browser
echo Skipped opening browser.

:end
echo.
echo Press any key to close this window...
pause >nul
