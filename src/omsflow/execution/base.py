from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from omsflow.models.order import OrderExecutionResult, Order


class ExecutionInterface(ABC):
    """Abstract base class for broker interfaces."""

    async def connect(self) -> None:
        """Establish connection to the broker."""
        pass

    async def disconnect(self) -> None:
        """Close connection to the broker."""
        pass

    @abstractmethod
    async def submit_order(
            self,
            order: Order,
    ) -> OrderExecutionResult:
        """Submit a new order to the broker."""
        pass

    @abstractmethod
    async def cancel_order(
            self,
            order: Order,
    ) -> OrderExecutionResult:
        """Cancel an existing order."""
        pass

    @abstractmethod
    async def get_order_status(
            self,
            order_id: str,
    ) -> OrderExecutionResult:
        """Get the current status of an order."""
        pass
