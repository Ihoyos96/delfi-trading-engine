#!/usr/bin/env bash
set -e

# Manage Redis shutdown on exit
cleanup() {
  if pgrep redis-server >/dev/null; then
    echo "Tearing down Redis..."
    redis-cli shutdown || true
  fi
}

# Trap signals to run cleanup
trap cleanup SIGINT SIGTERM EXIT

echo "Launching trading engine..."
# Pass any arguments through to the CLI
python -m src.main "$@" 