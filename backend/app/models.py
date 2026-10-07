"""Validated domain models for data, strategy events, trades, and research runs."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class StrategyStatus(StrEnum):
    PARTIALLY_SPECIFIED = "PARTIALLY_SPECIFIED"
    IMPLEMENTATION_PENDING = "IMPLEMENTATION_PENDING"
    FULLY_SPECIFIED = "FULLY_SPECIFIED"
    DETERMINISTIC = "DETERMINISTIC"


class Candle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    timeframe: Timeframe
    timestamp: datetime = Field(description="UTC candle close time")
    available_at: datetime = Field(description="Earliest instant this completed candle may be used")
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @field_validator("timestamp", "available_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @model_validator(mode="after")
    def valid_ohlc(self) -> "Candle":
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError("invalid OHLC relationship")
        if self.available_at < self.timestamp:
            raise ValueError("a candle cannot be available before its close timestamp")
        return self


class StrategyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    detection_timestamp: datetime
    source_candle_ids: list[UUID] = Field(default_factory=list)
    strategy_version: str
    quality_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", "detection_timestamp")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @model_validator(mode="after")
    def event_is_causal(self) -> "StrategyEvent":
        if self.detection_timestamp < self.timestamp:
            raise ValueError("detection cannot precede event formation")
        return self


class SwingPoint(StrategyEvent):
    price: float = Field(gt=0)
    kind: str
    formation_timestamp: datetime
    confirmation_timestamp: datetime

    @field_validator("formation_timestamp", "confirmation_timestamp")
    @classmethod
    def swing_times_are_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @model_validator(mode="after")
    def confirmation_is_not_early(self) -> "SwingPoint":
        if self.confirmation_timestamp < self.formation_timestamp or self.detection_timestamp < self.confirmation_timestamp:
            raise ValueError("a swing is usable only at or after confirmation")
        return self


class MarketStructure(StrategyEvent):
    classification: str
    sequence: list[UUID] = Field(default_factory=list)


class LiquidityLevel(StrategyEvent):
    price: float = Field(gt=0)
    originating_swing_ids: list[UUID] = Field(min_length=1)
    status: str
    already_swept: bool = False
    interactions: int = Field(default=0, ge=0)


class LiquiditySweep(StrategyEvent):
    liquidity_level_id: UUID
    sweep_extreme: float = Field(gt=0)
    close_after_sweep: float = Field(gt=0)
    distance_beyond_level: float = Field(ge=0)
    direction: Direction


class SupplyDemandZone(StrategyEvent):
    proximal_price: float = Field(gt=0)
    distal_price: float = Field(gt=0)
    direction: Direction
    mitigation_status: str
    displacement_id: UUID | None = None

    @model_validator(mode="after")
    def zone_boundaries_valid(self) -> "SupplyDemandZone":
        if self.proximal_price == self.distal_price:
            raise ValueError("zone boundaries must have nonzero width")
        return self


class Displacement(StrategyEvent):
    start_price: float = Field(gt=0)
    end_price: float = Field(gt=0)
    atr_at_start: float = Field(gt=0)
    magnitude_atr: float = Field(gt=0)
    direction: Direction
    bos_id: UUID | None = None


class BOS(StrategyEvent):
    broken_swing_id: UUID
    bos_price: float = Field(gt=0)
    direction: Direction
    confirmation_candle_id: UUID


class Setup(StrategyEvent):
    direction: Direction
    h1_bias: str
    m15_state: str
    liquidity_level_id: UUID
    sweep_id: UUID
    zone_id: UUID | None = None
    displacement_id: UUID | None = None
    bos_id: UUID | None = None
    variant: str
    expires_at: datetime | None = None


class Entry(BaseModel):
    timestamp: datetime
    price: float = Field(gt=0)
    model: str

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class Exit(BaseModel):
    timestamp: datetime
    price: float = Field(gt=0)
    reason: str

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class Trade(BaseModel):
    trade_id: UUID = Field(default_factory=uuid4)
    strategy_version: str
    symbol: str
    date: str
    timezone: str
    observation_window: str | None = None
    direction: Direction
    h1_bias: str
    m15_state: str
    liquidity_type: str | None = None
    liquidity_price: float | None = None
    sweep_timestamp: datetime | None = None
    sweep_price: float | None = None
    zone_type: str | None = None
    zone_high: float | None = None
    zone_low: float | None = None
    zone_timestamp: datetime | None = None
    confirmation_type: str
    confirmation_timestamp: datetime
    entry: Entry
    stop_price: float = Field(gt=0)
    target_price: float = Field(gt=0)
    risk_amount: float = Field(gt=0)
    position_size: float = Field(gt=0)
    spread: float = Field(ge=0)
    slippage: float = Field(ge=0)
    commission: float = Field(ge=0)
    exit: Exit
    pnl: float
    r_multiple: float
    mfe: float
    mae: float
    explanation: dict[str, Any] = Field(default_factory=dict)


class DataQualityReport(BaseModel):
    rows: int = Field(ge=0)
    duplicate_timestamps: int = Field(ge=0)
    input_chronological: bool
    gap_count: int = Field(ge=0)
    invalid_rows: int = Field(ge=0)
    weekend_rows: int = Field(ge=0)
    start_utc: datetime
    end_utc: datetime
    dataset_version: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ResearchRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    strategy_version: str
    strategy_status: StrategyStatus
    strategy_config: dict[str, Any]
    dataset_version: str
    dataset_date_range: tuple[datetime, datetime]
    symbols: list[str]
    timeframe: Timeframe
    timezone_config: dict[str, str]
    execution_assumptions: dict[str, Any]
    random_seed: int | None = None
    software_version: str
    git_commit: str | None = None

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)
