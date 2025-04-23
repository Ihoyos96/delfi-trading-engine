# AI Private Equity Trading Engine

A configurable framework for backtesting and live-trading strategies with plug‑and‑play brokers and data providers.

## Setup

Before you can use 1-second bar streaming, run the setup script to install Rust/Cargo and build the Rust bar aggregator:

```bash
chmod +x setup.sh
./setup.sh
```

This will install Rust via Homebrew (if needed) and compile `bar_aggregator` into `aggregator/target/release/bar_aggregator`.

## Running

Use the interactive CLI:

```bash
python -m src.cli.interactive
```

Or provide a JSON config:

```bash
python -m src.main config.json
```
