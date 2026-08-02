@echo off
REM Sandra Standard Launcher (v13.0) - use %~dp0 so symlink launch from starts/ works
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
