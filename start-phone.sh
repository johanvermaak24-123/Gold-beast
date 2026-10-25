#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/mobile"
npm ci
npx expo start --lan
