#!/usr/bin/env bash
# Quick launcher when developing from the repo (not the installed release).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
exec python3 -m chahlie --deck "$@"
