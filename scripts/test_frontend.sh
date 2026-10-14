#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend"
npm run api:check
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm run test:e2e
