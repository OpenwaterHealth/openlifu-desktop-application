@echo off
setlocal enabledelayedexpansion
REM docker-entrypoint.cmd
REM Wrapper that initializes the VS developer environment, then runs the build.
REM This is the ENTRYPOINT for the Windows Docker container.

echo =========================================
echo OpenLIFU Windows Docker Build
echo =========================================

REM ── Initialize Visual Studio developer environment ──
REM The VS environment is baked into the image's machine-level env vars,
REM but we call vcvarsall as a safety measure to ensure everything is set.
if exist "C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
    echo Refreshing Visual Studio environment...
    call "C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64
)

REM Verify cl.exe is available
where cl.exe >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo ERROR: cl.exe not found on PATH
    exit /b 1
)
echo Compiler found:
cl.exe 2>&1 | findstr /C:"Version"

REM Verify rc.exe is available; if not, find it and add its dir to PATH
where rc.exe >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo rc.exe not on PATH, searching Windows SDK directories...
    for /f "delims=" %%d in ('dir /s /b "C:\Program Files (x86)\Windows Kits\10\bin\*rc.exe" 2^>nul ^| findstr "x64\\rc.exe"') do (
        for %%p in ("%%~dpd") do (
            echo Adding SDK path: %%~dpp
            set "PATH=%%~dpp;!PATH!"
        )
    )
)
where rc.exe >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo WARNING: rc.exe still not found - link step may fail
) else (
    echo Resource compiler found:
    where rc.exe
)

REM ── Get build parameters from environment or use defaults ──
if "%BUILD_DIR%"=="" set BUILD_DIR=OR
if "%BUILD_TYPE%"=="" set BUILD_TYPE=Release
if "%QT5_DIR%"=="" set QT5_DIR=C:\Qt\5.15.2\msvc2019_64\lib\cmake\Qt5
if "%CMAKE_GENERATOR%"=="" set CMAKE_GENERATOR=Visual Studio 17 2022

echo BUILD_DIR   = %BUILD_DIR%
echo BUILD_TYPE  = %BUILD_TYPE%
echo QT5_DIR     = %QT5_DIR%
echo GENERATOR   = %CMAKE_GENERATOR%
echo =========================================

REM ── Locate source directory ──
set SRC_DIR=
if exist "C:\workspace\CMakeLists.txt" (
    set SRC_DIR=C:\workspace
) else if exist "C:\W\O\CMakeLists.txt" (
    set SRC_DIR=C:\W\O
) else (
    echo ERROR: Source directory not found. Mount the repo at C:\workspace or clone to C:\W\O
    exit /b 1
)
echo Using source directory: %SRC_DIR%

REM ── Prepare build directory ──
set BUILD_PATH=C:\W\%BUILD_DIR%
if not exist "%BUILD_PATH%" mkdir "%BUILD_PATH%"

REM Remove stale CMake cache
if exist "%BUILD_PATH%\CMakeCache.txt" (
    echo Removing stale CMakeCache.txt from previous run
    del /f "%BUILD_PATH%\CMakeCache.txt"
    if exist "%BUILD_PATH%\CMakeFiles" rmdir /s /q "%BUILD_PATH%\CMakeFiles"
)

REM ── Configure ──
REM CMAKE_GENERATOR_INSTANCE tells CMake where VS Build Tools are installed.
REM CMAKE_SYSTEM_VERSION forces the Windows SDK version to the one we installed.
echo Configuring with CMake...
cmake -G "%CMAKE_GENERATOR%" -A x64 ^
    -DQt5_DIR:PATH="%QT5_DIR%" ^
    -DCMAKE_BUILD_TYPE:STRING=%BUILD_TYPE% ^
    -DCMAKE_GENERATOR_INSTANCE:INTERNAL="C:/BuildTools" ^
    -DCMAKE_SYSTEM_VERSION=10.0.22621.0 ^
    -S "%SRC_DIR%" -B "%BUILD_PATH%"

if !ERRORLEVEL! neq 0 (
    echo ERROR: CMake configure failed with exit code !ERRORLEVEL!
    exit /b !ERRORLEVEL!
)

REM ── Build ──
echo Building (this may take several hours)...
cmake --build "%BUILD_PATH%" --config %BUILD_TYPE% -- /maxcpucount
if !ERRORLEVEL! neq 0 (
    echo ERROR: Build failed with exit code !ERRORLEVEL!
    exit /b !ERRORLEVEL!
)

REM ── Package ──
set INNER_BUILD=%BUILD_PATH%\Slicer-build
if exist "%INNER_BUILD%" (
    echo Found inner Slicer build at %INNER_BUILD%; running PACKAGE target...
    cmake --build "%INNER_BUILD%" --config %BUILD_TYPE% --target PACKAGE
    if !ERRORLEVEL! neq 0 (
        echo WARNING: Package step failed; continuing to archive...
    )
)

REM ── Copy artifacts to output ──
if not exist "C:\output" mkdir "C:\output"

REM Copy any generated installers
if exist "%INNER_BUILD%" (
    echo Copying installer artifacts from %INNER_BUILD%...
    for /r "%INNER_BUILD%" %%f in (OpenLIFU*.exe) do (
        echo   Copying %%f
        copy "%%f" "C:\output\" /y
    )
)

REM Create a zip archive of the build
echo Archiving build output...
powershell -NoLogo -Command ^
    "$ts = Get-Date -Format 'yyyyMMddHHmmss'; " ^
    "$src = if (Test-Path '%INNER_BUILD%') { '%INNER_BUILD%' } else { '%BUILD_PATH%' }; " ^
    "Compress-Archive -Path $src -DestinationPath \"C:\output\openlifu-build-$ts.zip\" -Force; " ^
    "Write-Host \"Archive: openlifu-build-$ts.zip\""

echo =========================================
echo Build complete! Artifacts in C:\output
echo =========================================
