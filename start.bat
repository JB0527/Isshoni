@echo off
REM Isshoni Quick Start Script for Windows
REM This script helps you get started quickly

echo.
echo   _____ _____ _____ _    _  ____  _   _ _____
echo  ^|_   _/ ____/ ____^| ^|  ^| ^|/ __ \^| \ ^| ^|_   _^|
echo    ^| ^|^| (___^| (___^| ^|__^| ^| ^|  ^| ^|  \^| ^| ^| ^|
echo    ^| ^| \___ \\___ \^|  __  ^| ^|  ^| ^| . ` ^| ^| ^|
echo   _^| ^|_____) ^|___) ^| ^|  ^| ^| ^|__^| ^| ^|\  ^|_^| ^|_
echo  ^|_____^|____/_____/^|_^|  ^|_^|\____/^|_^| \_^|_____^|
echo.
echo  AI-Powered Visual Infrastructure Generator
echo  一緒に (Together) - Build cloud infrastructure with AI
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    exit /b 1
)

echo [OK] Docker is installed

REM Check if .env exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo [OK] .env file created
    echo.
    echo IMPORTANT: Please edit .env file with your credentials:
    echo    - AWS_ACCESS_KEY_ID
    echo    - AWS_SECRET_ACCESS_KEY
    echo    - ANTHROPIC_API_KEY or OPENAI_API_KEY
    echo.
    pause
)

REM Start services
echo Starting Isshoni services...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check backend
curl -s http://localhost:8000/ >nul 2>&1
if errorlevel 1 (
    echo Error: Backend failed to start
    echo Check logs with: docker-compose logs backend
    exit /b 1
)
echo [OK] Backend is ready

REM Check frontend
curl -s http://localhost:8501/_stcore/health >nul 2>&1
if errorlevel 1 (
    echo Error: Frontend failed to start
    echo Check logs with: docker-compose logs frontend
    exit /b 1
)
echo [OK] Frontend is ready

echo.
echo ========================================
echo    Isshoni is ready! 🎉
echo ========================================
echo.
echo Access your application:
echo   Frontend UI:      http://localhost:8501
echo   Backend API:      http://localhost:8000
echo   API Docs:         http://localhost:8000/docs
echo.
echo Quick commands:
echo   View logs:        docker-compose logs -f
echo   Stop services:    docker-compose down
echo   Restart:          docker-compose restart
echo.
echo Documentation:
echo   Quick Start:      type QUICKSTART.md
echo   Architecture:     type ARCHITECTURE.md
echo   Deployment:       type DEPLOYMENT_GUIDE.md
echo.
echo Happy building! 一緒に (Let's build together!)
echo.

REM Open browser
choice /C YN /M "Open browser now"
if errorlevel 2 goto :end
if errorlevel 1 start http://localhost:8501

:end
pause
