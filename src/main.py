# Load environment variables from .env in current directory or parents
from dotenv import load_dotenv
load_dotenv(override=True)
print("Loaded environment")

import argparse
from src.cli.interactive import interactive_start
from src.cli.configured import run_configured
from src.engine import run_from_config


def main():
    """Main entry point for the trading engine."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="High‑edge trading engine entry point")
    parser.add_argument(
        '--configured', action='store_true',
        help="Run using the configuration file"
    )
    parser.add_argument(
        '--config-file', default='config.json',
        help="Path to the configuration file"
    )
    args = parser.parse_args()

    # Load configuration via interactive or file-driven branch
    if args.configured:
        cfg = run_configured(args.config_file)
    else:
        cfg = interactive_start()

    if cfg is None:
        print("No configuration provided. Exiting.")
        return

    # Execute engine with the loaded config
    run_from_config(cfg)


if __name__ == '__main__':
    main()
