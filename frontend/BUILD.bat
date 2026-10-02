@echo off
REM ================================================
REM  Frontend Builder - Uses Node directly (no npm needed)
REM ================================================
cd /d "%~dp0"

echo ================================================
echo  Building Frontend...
echo  Dir: %cd%
echo ================================================
echo.

REM 检查 node 是否可用
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found on this system.
    echo.
    echo  Please download and install Node.js:
    echo    Visit: https://nodejs.org/
    echo    Download the LTS version (v18.x or v20.x)
    echo.
    echo  After installing, re-run this script.
    echo.
    pause
    exit /b 1
)

echo [INFO] Node found:
node --version
echo.

REM 检查 vite 是否可用（直接调用本地 node_modules 中的 vite）
if not exist "node_modules\vite\bin\vite.js" (
    echo [ERROR] Vite not found in node_modules.
    echo  Please run: npm install  (after installing Node.js)
    echo.
    pause
    exit /b 1
)

echo [INFO] Running Vite build...
echo.

REM 直接用 node 调用 vite 来构建
node node_modules\vite\bin\vite.js build

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo  BUILD SUCCESSFUL!
    echo  New frontend files generated in: dist\
    echo.
    echo  Next: Restart your backend (START.bat) to serve
    echo         the new frontend, then refresh browser (Ctrl+F5).
    echo ================================================
) else (
    echo.
    echo ================================================
    echo  BUILD FAILED!
    echo  Please check the error messages above.
    echo ================================================
)

echo.
pause
