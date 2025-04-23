#!/usr/bin/env bash
set -e

echo -e "\033[34mRunning setup for delfi-trading-engine...\033[0m\n"

# Ensure Poetry is installed
if ! command -v poetry >/dev/null; then
  echo -e "\n\033[31mPoetry not found;\033[34m installing via official installer...\033[0m"
  curl -sSL https://install.python-poetry.org | python3 -
  # Add Poetry to PATH for this session
  export PATH="$HOME/.local/bin:$PATH"
else
  echo -e "\033[38;5;208mPoetry already installed: $(poetry --version)\033[0m\n"
fi

# Install Python dependencies
poetry install --no-root

# Ensure Homebrew is installed
if ! command -v brew >/dev/null; then
  echo "Error: Homebrew not found. Please install Homebrew first: https://brew.sh/"
  exit 1
fi

# Ensure Cargo (Rust) is installed
if ! command -v cargo >/dev/null; then
  echo -e "\n\033[34mRust/Cargo not found; installing via Homebrew...\033[0m"
  brew update
  brew install rust
else
  echo -e "\n\033[38;5;208mRust/Cargo already installed: $(cargo --version)\033[0m\n"
fi

# Ensure Redis is installed
if ! command -v redis-server >/dev/null; then
  echo "Redis not found; installing via Homebrew..."
  brew update
  brew install redis
else
  echo -e "\033[38;5;208mRedis already installed: $(redis-server --version)\033[0m\n"
fi

# Build the Rust bar_aggregator binary
AGG_PATH="$(dirname "$0")/aggregator"
if [ -d "$AGG_PATH" ]; then
  echo -e "\033[34mBuilding bar_aggregator in release mode...\033[0m"
  pushd "$AGG_PATH" >/dev/null
  cargo build --release
  popd >/dev/null
  echo -e "\033[32mbar_aggregator built at $AGG_PATH/target/release/bar_aggregator\033[0m\n"
else
  echo -e "\033[33mWarning: aggregator directory not found at $AGG_PATH. Skipping build.\033[0m"
fi

echo -e "\n\033[32mSetup complete.\033[0m" 