from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any


class PhxOrderStatus(str, Enum):
    ACCEPTED = 'Accepted'
    CALCULATED = 'Calculated'
    CANCELED = 'Canceled'
    DONE_FOR_DAY = 'DoneForDay'
    EXPIRED = 'Expired'
    FILLED = 'Filled'
    PARTIAL = 'Partial'
    PENDING_CANCEL = 'PendingCancel'
    PENDING_NEW = 'PendingNew'
    PENDING_REPLACE = 'PendingReplace'
    REJECTED = 'Rejected'
    REPLACED = 'Replaced'
    STOPPED = 'Stopped'
    SUSPENDED = 'Suspended'
    Unknown = 'Unknown'

    @property
    def is_success(self) -> bool:
        success_statuses = [self.FILLED]
        return self in success_statuses

    @property
    def is_canceled(self) -> bool:
        cancel_statuses = [self.CANCELED]
        return self in cancel_statuses

    @property
    def is_partial(self) -> bool:
        partial_statuses = [self.PARTIAL]
        return self in partial_statuses


class PhxIdType(str, Enum):
    CURRENCY_PAIR = "CURRENCY_PAIR"
    BBG_TICKER = "BBG_TICKER"
    BAM_SYMBOL = "BAM_SYMBOL"


class PhxExecutionStyle(str, Enum):
    AUTO_MARKET = 'AUTO_MARKET'
    FIVE_MINUTES_TWAP = 'FIVE_MINUTES_TWAP'
    FIVE_MINUTES_IS = 'FIVE_MINUTES_IS'
    TEN_MINUTES_IS = 'TEN_MINUTES_IS'
    IS_NEUTRAL = 'IS_NEUTRAL'
    LIMIT_GS = 'LIMIT_GS'


class PhxSecurityType(str, Enum):
    FX_SPOT = "FX_SPOT"
    FUT = "FUT"
    FX_FWD = "FX_FWD"
    FX_SWAP = "FX_SWAP"
    VAR_VOL_SWAP = "VAR_VOL_SWAP"
