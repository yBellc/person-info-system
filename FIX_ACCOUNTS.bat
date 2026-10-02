@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Fix Test Accounts - Unlock and Reset Passwords
echo ============================================================
echo.
"D:\python\python.exe" "%~dp0FIX_ACCOUNTS.py"
echo.
echo Press any key to close...
pause >nul
