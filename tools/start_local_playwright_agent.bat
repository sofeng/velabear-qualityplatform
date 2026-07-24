@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_local_playwright_agent.ps1" %*
exit /b %ERRORLEVEL%
