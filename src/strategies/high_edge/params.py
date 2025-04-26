from pydantic import BaseModel, Field
from src.config.config import Period

class HighEdgeParams(BaseModel):
    """Runtime parameters for High Edge strategy"""
    symbol: str
    timeframe: str = Field("1Min")
    period: Period
    # EMA windows for momentum filter
    short_window: int = Field(5, ge=1)
    long_window: int = Field(60, ge=1)
    ema_threshold: float = Field(0.001, gt=0)  # deadband as fraction of price
    # VWAP z-score window and threshold
    zscore_window: int = Field(60, ge=1)
    zscore_threshold: float = Field(1.0, gt=0)
    # ATR-based stops and targets
    atr_window: int = Field(1, ge=1)
    stop_atr_mult: float = Field(1.2, gt=0)
    target_mult: float = Field(1.8, gt=0)
    # Position size and entry cooldown (number of bars)
    size: float = Field(1.0, gt=0)
    cooldown: int = Field(5, ge=0)
    # Risk controls: daily drawdown cap and concurrent position limits
    daily_drawdown: float = Field(0.03, ge=0)  # max fraction drawdown from start equity
    max_total_positions: int = Field(10, ge=1)  # max open positions total
    max_positions_per_symbol: int = Field(3, ge=1)  # max open positions per symbol 