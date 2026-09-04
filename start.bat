@echo off
setlocal enabledelayedexpansion
title RiskRadar Launcher

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ================================================
echo   RiskRadar - AI Safety Investigator
echo   One-click launcher (backend + frontend)
echo ================================================
echo.

REM --- Backend: create venv if missing ---
if exist "%ROOT%\backend\venv\Scripts\activate.bat" goto backend_venv_ready
echo [1/4] Creating Python virtual environment for backend...
python -m venv "%ROOT%\backend\venv"
if errorlevel 1 (
    echo.
    echo Failed to create a virtual environment. Is Python installed and on PATH?
    pause
    exit /b 1
)

:backend_venv_ready
echo [2/4] Checking backend dependencies...
pushd "%ROOT%\backend"
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
call venv\Scripts\deactivate.bat
popd

REM --- Frontend: npm install if missing ---
if exist "%ROOT%\frontend\node_modules" goto frontend_ready
echo [3/4] Installing frontend dependencies (first run only, this can take a minute)...
pushd "%ROOT%\frontend"
call npm install
popd

:frontend_ready
echo [4/4] Launching backend and frontend servers...
echo.

start "RiskRadar Backend" /D "%ROOT%\backend" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
start "RiskRadar Frontend" /D "%ROOT%\frontend" cmd /k "npm run dev"

echo Waiting for servers to warm up...
timeout /t 6 /nobreak >nul

start "" "http://localhost:5173"

echo.
echo RiskRadar is running:
echo   Backend  : http://127.0.0.1:8000
echo   Frontend : http://localhost:5173
echo.
echo Two new windows were opened for the backend and frontend logs.
echo Close those windows (or Ctrl+C inside them) to stop RiskRadar.
echo This window can be closed safely.
echo.
pause >nul
endlocal
