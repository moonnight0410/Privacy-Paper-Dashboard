@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"
set "ROOT=%~dp0"

if "%~1"=="--check" goto CHECK_ONLY

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3 and add it to PATH.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js was not found. Please install Node.js LTS and add it to PATH.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found. Please install Node.js LTS.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating backend virtual environment...
    python -m venv .venv
    if errorlevel 1 pause & exit /b 1
)

echo Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 pause & exit /b 1
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 pause & exit /b 1

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        pause
        exit /b 1
    )
    popd
)

echo Building frontend assets...
pushd frontend
call npm run build
if errorlevel 1 (
    popd
    pause
    exit /b 1
)
popd

echo Starting app at http://127.0.0.1:8000/
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -WindowStyle Minimized -FilePath '%ROOT%.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%ROOT%'"

timeout /t 4 /nobreak >nul
echo App is ready at http://127.0.0.1:8000/
exit /b 0

:CHECK_ONLY
where python >nul 2>nul || exit /b 1
where node >nul 2>nul || exit /b 1
where npm >nul 2>nul || exit /b 1
echo start.bat prerequisites are available.
exit /b 0
