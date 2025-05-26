from enum import Enum
from typing import Dict, Optional, Type
from omsflow.models.phoenix import PhxOrderStatus

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"
    VWAP = "VWAP"


class SecurityType(str, Enum):
    EQUITY = "EQUITY"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    FOREX = "FOREX"


class Order(BaseModel):
    """Base order model representing a financial order."""

    order_id: UUID = Field(default_factory=uuid4)
    client_order_id: str
    symbol: str
    security_type: SecurityType
    side: str  # BUY/SELL
    quantity: float
    order_type: OrderType
    time_in_force: TimeInForce
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("price")
    def validate_price(cls, v: Optional[float], values: Dict[str, Any]) -> Optional[float]:
        if values.get("order_type") == OrderType.LIMIT and v is None:
            raise ValueError("Limit orders must have a price")
        return v

    @field_validator("side")
    def validate_side(cls, v: str) -> str:
        if v.upper() not in ["BUY", "SELL"]:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
        return v.upper()


class OrderValidationResult(BaseModel):
    """Result of order validation."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OrderExecutionResult(BaseModel):
    """Result of order execution attempt."""

    success: bool
    order_id: UUID
    execution_id: Optional[str] = None
    error_message: Optional[str] = None
    broker_order_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)