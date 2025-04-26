from src.strategies.ema_crossover.params import EMACrossoverParams
from src.strategies.ema_crossover.strategy import EMACrossoverStrategy
from src.strategies.high_edge.strategy import HighEdgeStrategy
from src.strategies.high_edge.params import HighEdgeParams

# Single source of truth for all strategies
STRATEGY_CONFIG = {
    EMACrossoverStrategy.__name__: {
        "display_name": "EMA Crossover",
        "strategy_class": EMACrossoverStrategy,
        "config_model": EMACrossoverParams
    },
    HighEdgeStrategy.__name__: {
        "display_name": "High Edge",
        "strategy_class": HighEdgeStrategy,
        "config_model": HighEdgeParams
    },
    # Future strategies can be added here
} 