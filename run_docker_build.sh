#!/usr/bin/env bash
set -euo pipefail

# Helper script to build the docker image and run the build, placing artifacts
# into ./docker-build directory.

IMAGE_NAME="openlifu-builder:latest"

docker build -t "$IMAGE_NAME" .

mkdir -p docker-build

# Run container: mount repository as /workspace and host docker-build as /output
docker run --rm -v "$PWD":/workspace -w /workspace -v "$PWD"/docker-build:/output "$IMAGE_NAME"

echo "Artifacts placed in ./docker-build"
