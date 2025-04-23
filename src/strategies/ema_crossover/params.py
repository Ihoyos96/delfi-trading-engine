from pydantic import BaseModel, Field
from src.config.config import Period

class EMACrossoverParams(BaseModel):
    symbol: str
    timeframe: str = Field("1Min")
    period: Period
    short_window: int = Field(5, ge=1)
    long_window: int = Field(20, ge=1)
    size: float = Field(1.0, gt=0) 