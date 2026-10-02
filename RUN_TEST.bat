@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  P0-1 E2E Test: Expense Reimbursement Full Flow
echo ============================================================
echo.
"D:\python\python.exe" "%~dp0e2e_test.py"
echo.
echo Press any key to close...
pause >nul
