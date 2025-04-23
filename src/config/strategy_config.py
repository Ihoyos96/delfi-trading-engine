from src.strategies.ema_crossover.params import EMACrossoverParams
from src.strategies.ema_crossover.strategy import EMACrossoverStrategy

# Single source of truth for all strategies
STRATEGY_CONFIG = {
    EMACrossoverStrategy.__name__: {
        "display_name": "EMA Crossover",
        "strategy_class": EMACrossoverStrategy,
        "config_model": EMACrossoverParams
    },
    # Future strategies can be added here
} 