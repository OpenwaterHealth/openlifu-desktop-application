# docker-entrypoint.ps1
# Entry point for building OpenLIFU inside a Windows container.
# Expects the repository root to be mounted at C:\workspace and an output
# directory mounted at C:\output.

$ErrorActionPreference = 'Stop'

# ── Parameters with defaults ──
$BuildDir   = if ($env:BUILD_DIR)   { $env:BUILD_DIR }   else { 'OR' }
$BuildType  = if ($env:BUILD_TYPE)  { $env:BUILD_TYPE }  else { 'Release' }
$Qt5Dir     = if ($env:QT5_DIR)     { $env:QT5_DIR }     else { 'C:\Qt\5.15.2\msvc2019_64\lib\cmake\Qt5' }
$Generator  = if ($env:CMAKE_GENERATOR) { $env:CMAKE_GENERATOR } else { 'Visual Studio 17 2022' }

Write-Host "========================================="
Write-Host "OpenLIFU Windows Docker Build"
Write-Host "========================================="
Write-Host "BUILD_DIR   = $BuildDir"
Write-Host "BUILD_TYPE  = $BuildType"
Write-Host "QT5_DIR     = $Qt5Dir"
Write-Host "GENERATOR   = $Generator"
Write-Host "========================================="

# ── Initialize Visual Studio developer environment ──
$vsPath = 'C:\BuildTools'
$vcvarsall = Join-Path $vsPath 'VC\Auxiliary\Build\vcvarsall.bat'

if (-not (Test-Path $vcvarsall)) {
    Write-Error "vcvarsall.bat not found at $vcvarsall"
    exit 1
}

Write-Host "Initializing Visual Studio environment..."
# Run vcvarsall and capture the resulting environment
cmd /c "`"$vcvarsall`" amd64 && set" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
Write-Host "Visual Studio environment initialized."

# ── Locate source directory ──
# When the repo is mounted at C:\workspace, look for it there first,
# then fall back to the working directory C:\W
$SrcDir = $null
if (Test-Path 'C:\workspace\CMakeLists.txt') {
    $SrcDir = 'C:\workspace'
} elseif (Test-Path 'C:\W\O\CMakeLists.txt') {
    $SrcDir = 'C:\W\O'
} else {
    Write-Error "Source directory not found. Mount the repo at C:\workspace or clone to C:\W\O"
    exit 1
}
Write-Host "Using source directory: $SrcDir"

# ── Configure ──
$BuildPath = "C:\W\$BuildDir"
if (-not (Test-Path $BuildPath)) {
    New-Item -ItemType Directory -Path $BuildPath -Force | Out-Null
}

# Remove stale CMake cache to avoid source-directory mismatch errors
$cacheFile = Join-Path $BuildPath 'CMakeCache.txt'
if (Test-Path $cacheFile) {
    Write-Host "Removing stale CMakeCache.txt from previous run"
    Remove-Item $cacheFile -Force
    $cmakeFiles = Join-Path $BuildPath 'CMakeFiles'
    if (Test-Path $cmakeFiles) {
        Remove-Item $cmakeFiles -Recurse -Force
    }
}

Write-Host "Configuring with CMake..."
cmake -G "$Generator" -A x64 `
    "-DQt5_DIR:PATH=$Qt5Dir" `
    "-DCMAKE_BUILD_TYPE:STRING=$BuildType" `
    -S "$SrcDir" -B "$BuildPath"

if ($LASTEXITCODE -ne 0) {
    Write-Error "CMake configure failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# ── Build ──
Write-Host "Building (this may take several hours)..."
cmake --build "$BuildPath" --config $BuildType -- /maxcpucount

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# ── Package ──
$InnerBuild = Join-Path $BuildPath 'Slicer-build'
if (Test-Path $InnerBuild) {
    Write-Host "Found inner Slicer build at $InnerBuild; running PACKAGE target..."
    cmake --build "$InnerBuild" --config $BuildType --target PACKAGE
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Package step failed (exit code $LASTEXITCODE); continuing to archive..." -ForegroundColor Yellow
    }
}

# ── Copy artifacts to output ──
$OutputDir = 'C:\output'
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Copy any generated installers (NSIS .exe)
$installers = Get-ChildItem -Path $BuildPath -Recurse -Filter '*.exe' |
    Where-Object { $_.Name -match 'OpenLIFU.*\.(exe)$' -or $_.Name -match 'install' }
foreach ($installer in $installers) {
    Write-Host "Copying installer: $($installer.FullName)"
    Copy-Item $installer.FullName -Destination $OutputDir -Force
}

# Create a zip archive of the build output
$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$archiveName = "openlifu-build-$timestamp.zip"
$archivePath = Join-Path $OutputDir $archiveName

if (Test-Path $InnerBuild) {
    Write-Host "Archiving inner build to $archivePath..."
    Compress-Archive -Path $InnerBuild -DestinationPath $archivePath -Force
} else {
    Write-Host "Archiving build directory to $archivePath..."
    Compress-Archive -Path $BuildPath -DestinationPath $archivePath -Force
}

Write-Host "========================================="
Write-Host "Build complete! Artifacts in C:\output"
Write-Host "Archive: $archiveName"
Write-Host "========================================="
