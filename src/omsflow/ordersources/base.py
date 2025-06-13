from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, AsyncIterable

from omsflow.models.order import Order


class OrderSource(ABC):
    """Abstract base class for order ordersources."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the order source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the order source."""
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve a single order by its ID."""
        pass

    @abstractmethod
    @property
    def new_orders(self) -> AsyncIterable[Order]:
        """Property that returns an async iterable of new orders."""
        pass

    @abstractmethod
    async def acknowledge_order(self, order_id: str) -> bool:
        """Acknowledge successful processing of an order."""
        pass
