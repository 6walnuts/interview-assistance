#!/usr/bin/env bash
# Build all code-execution sandbox images.
set -euo pipefail
cd "$(dirname "$0")"
for lang in python javascript go java cpp; do
  echo "==> ai-coach-sandbox-${lang}"
  docker build -t "ai-coach-sandbox-${lang}:latest" -f "Dockerfile.${lang}" .
done
