#!/bin/bash
set -euo pipefail

# Entry point for building OpenLIFU inside the container.
# Expects the repository root to be mounted at /workspace and an output
# directory mounted to /output (host: ./docker-build -> container: /output).

export BUILD_DIR="${BUILD_DIR:-OpenLIFU-superbuild}"
export BUILD_TYPE="${BUILD_TYPE:-Release}"
export QT5_DIR="${QT5_DIR:-/opt/qt/5.15.2/gcc_64/lib/cmake/Qt5}"

mkdir -p /output
cd /workspace

echo "Using BUILD_DIR=$BUILD_DIR, BUILD_TYPE=$BUILD_TYPE, QT5_DIR=$QT5_DIR"


# Locate source directory.
# When the container mounts the repo root into /workspace the top-level
# CMakeLists.txt (the Slicer superbuild) is the correct entry point.
# If someone clones into a sub-folder called OpenLIFU-app, use that instead.
if [ -d ./OpenLIFU-app ] && [ -f ./OpenLIFU-app/CMakeLists.txt ]; then
  SRC_DIR=./OpenLIFU-app
elif [ -f ./CMakeLists.txt ]; then
  SRC_DIR=.
else
  echo "Error: source directory not found in /workspace (looked for OpenLIFU-app/, then repo root CMakeLists.txt)" >&2
  ls -la /workspace
  exit 1
fi

mkdir -p "$BUILD_DIR"

# Remove stale CMake cache to avoid source-directory mismatch errors
if [ -f "$BUILD_DIR/CMakeCache.txt" ]; then
  echo "Removing stale CMakeCache.txt from previous run"
  rm -f "$BUILD_DIR/CMakeCache.txt"
  rm -rf "$BUILD_DIR/CMakeFiles"
fi

echo "Using source directory: $SRC_DIR"
cmake -DCMAKE_BUILD_TYPE:STRING="$BUILD_TYPE" -DQt5_DIR:PATH="$QT5_DIR" -S "$SRC_DIR" -B "$BUILD_DIR"

make -C "$BUILD_DIR" -j"$(nproc)"

# If there is an inner Slicer build, try to package it; otherwise archive the build dir
INNER_BUILD="$BUILD_DIR/Slicer-build"
if [ -d "$INNER_BUILD" ]; then
  echo "Found inner build at $INNER_BUILD; running package if available"
  if make -C "$INNER_BUILD" package; then
    echo "Package step completed"
  else
    echo "Package step failed or not available; continuing to archive build" >&2
  fi
  TAR_SRC="$INNER_BUILD"
else
  TAR_SRC="$BUILD_DIR"
fi

ARCHIVE_NAME="openlifu-build-$(date +%Y%m%d%H%M%S).tar.gz"
tar -C "$(dirname "$TAR_SRC")" -czf "/output/$ARCHIVE_NAME" "$(basename "$TAR_SRC")"

echo "Build artifacts written to /output/$ARCHIVE_NAME"
