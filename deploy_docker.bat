@echo off
REM ============================================
REM Bilibili Video Transcription API - Docker Deploy Script
REM ============================================

setlocal enabledelayedexpansion

REM Configuration
set IMAGE_NAME=bilibili-video-api
set CONTAINER_NAME=bilibili-video-api
set PORT=5000
set DOCKERFILE_PATH=%~dp0

echo ============================================
echo Bilibili Video Transcription API - Docker Deploy
echo ============================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Stop and remove existing container
echo [1/4] Cleaning up existing container...
docker stop %CONTAINER_NAME% >nul 2>&1
docker rm %CONTAINER_NAME% >nul 2>&1

REM Build Docker image
echo [2/4] Building Docker image...
echo This may take 10 minutes on first build (model download)...
echo.
docker build -t %IMAGE_NAME% "%DOCKERFILE_PATH%"
if errorlevel 1 (
    echo [ERROR] Docker build failed.
    pause
    exit /b 1
)

REM Run container
echo [3/4] Starting container...
docker run -d -p %PORT%:5000 --name %CONTAINER_NAME% %IMAGE_NAME%
if errorlevel 1 (
    echo [ERROR] Failed to start container.
    pause
    exit /b 1
)

REM Wait for service to be ready
echo [4/4] Waiting for service to be ready...
echo.

REM Wait for health check (max 60 seconds)
set /a counter=0
:wait_loop
if !counter! GEQ 12 (
    echo [WARNING] Health check timeout, but container is starting.
    goto start_complete
)

ping -n 5 127.0.0.1 >nul 2>&1

REM Check if container is running
docker ps --filter "name=%CONTAINER_NAME%" --filter "status=running" | findstr %CONTAINER_NAME% >nul
if errorlevel 1 (
    echo [ERROR] Container stopped unexpectedly.
    docker logs %CONTAINER_NAME%
    pause
    exit /b 1
)

set /a counter+=1
echo Waiting... !counter!/12
goto wait_loop

:start_complete

echo.
echo ============================================
echo Deployment Complete!
echo ============================================
echo.
echo Service URLs:
echo   - Health Check: http://localhost:%PORT%/api/v1/health
echo   - API Docs:     http://localhost:%PORT%/docs
echo.
echo Docker Commands:
echo   - View logs:    docker logs -f %CONTAINER_NAME%
echo   - Stop:        docker stop %CONTAINER_NAME%
echo   - Start:       docker start %CONTAINER_NAME%
echo   - Remove:      docker rm %CONTAINER_NAME%
echo.
echo API Usage:
echo   - Submit: curl -X POST http://localhost:%PORT%/api/v1/transcribe -H "Content-Type: application/json" -d '{"input": "BV1xx411c7mD"}'
echo   - Status: curl http://localhost:%PORT%/api/v1/status/JOB_ID
echo.
pause
