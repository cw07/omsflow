from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from omsflow.core.models import Order


class OrderSource(ABC):
    """Abstract base class for order sources."""
    
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
    async def stream_orders(self) -> AsyncIterator[Order]:
        """Stream orders from the source."""
        pass

    @abstractmethod
    async def acknowledge_order(self, order_id: str) -> bool:
        """Acknowledge successful processing of an order."""
        pass


class SQLOrderSource(OrderSource):
    """Base class for SQL-based order sources."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None

    @abstractmethod
    async def execute_query(self, query: str, params: dict) -> list[dict]:
        """Execute a SQL query and return results."""
        pass


class RedisOrderSource(OrderSource):
    """Base class for Redis-based order sources."""
    
    def __init__(self, host: str, port: int, stream_key: str):
        self.host = host
        self.port = port
        self.stream_key = stream_key
        self._client = None

    @abstractmethod
    async def add_to_dead_letter_queue(self, order: Order, error: str) -> None:
        """Add a failed order to the dead letter queue."""
        pass 