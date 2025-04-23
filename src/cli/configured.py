from src.config.config import load_config, Config


def run_configured(config_file: str) -> Config:
    """Load and return the project's Config model from a JSON config file."""
    return load_config(config_file) 