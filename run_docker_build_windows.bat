@echo off
REM run_docker_build_windows.bat
REM Helper script to build the Windows Docker image and run the build,
REM placing artifacts into .\docker-build-windows directory.
REM
REM Prerequisites:
REM   - Docker Desktop for Windows with Windows containers enabled
REM     (right-click Docker tray icon -> "Switch to Windows containers...")
REM   - Enough disk space (~50GB+ for VS Build Tools + Qt + Slicer build)

setlocal enabledelayedexpansion

set IMAGE_NAME=openlifu-builder-windows:latest

echo =========================================
echo Building Windows Docker image: %IMAGE_NAME%
echo =========================================

docker build -f Docker.windows -t %IMAGE_NAME% .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker image build failed.
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Running build container...
echo =========================================

if not exist docker-build-windows mkdir docker-build-windows

REM Mount the repo as C:\workspace and output dir as C:\output
docker run --rm ^
    -v "%CD%":C:\workspace ^
    -v "%CD%\docker-build-windows":C:\output ^
    -m 8g ^
    %IMAGE_NAME%

if %ERRORLEVEL% neq 0 (
    echo ERROR: Container build failed.
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Build complete! Artifacts in .\docker-build-windows
echo =========================================

endlocal
