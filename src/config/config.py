from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal
from datetime import date
import json

class Period(BaseModel):
    start: date
    end: date

class SimulationConfig(BaseModel):
    start_cash: float = Field(100000)
    slippage: float = Field(0.0001)
    commission: float = Field(0.0002)
    timeframe: str = Field("1Min")
    period: Period = Field(Period(start=date.today(), end=date.today()))

class StrategyItem(BaseModel):
    name: str
    enabled: bool = Field(True)
    operation: Literal["backtest", "live"] = Field("backtest")
    paper: bool = Field(False)
    shadow_mode: bool = Field(False)
    config: Dict[str, Any]

class BrokerItem(BaseModel):
    """Configuration for selecting and parameterizing a broker."""
    name: str
    config: Dict[str, Any]

class DataProviderItem(BaseModel):
    """Configuration for selecting and parameterizing a data provider."""
    name: str
    config: Dict[str, Any]

class Config(BaseModel):
    simulation: SimulationConfig
    broker: BrokerItem
    data_provider: DataProviderItem
    strategies: List[StrategyItem]

    class Config:
        validate_by_name = True


def load_config(path: str) -> Config:
    """Load and validate JSON config, returning a Config instance."""
    try:
        with open(path) as f:
            data = json.load(f)
        return Config.model_validate(data)
    except FileNotFoundError:
        raise FileNotFoundError("Config file missing (Expected config.json at root)")