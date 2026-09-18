#!/usr/bin/env bash
# Collect all TSX syntax errors with esbuild in a node container.
set -uo pipefail
cd /home/ubuntu/SandboxHub/apps/web
docker run --rm -v /home/ubuntu/SandboxHub/apps/web:/app -w /app node:20-alpine \
  sh -c 'npx --yes esbuild@0.21.5 "src/**/*.tsx" --loader:.tsx=tsx --outdir=/tmp/out --log-limit=300' 2>&1 | head -80
