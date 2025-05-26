from typing import AsyncIterator, Any
from omsflow.ordersources.base import OrderSource


class RedisOrderSource(OrderSource):
    """Base class for Redis - based order sources."""

    def __init__(self, host: str, port: int, stream_key: str):
        self.host = host
        self.port = port
        self.stream_key = stream_key
        self._client = None

    def connect(self) -> None:
        pass

    async def stream_orders(self) -> AsyncIterator[Any]:
        pass

    async def acknowledge_order(self, order_id: str) -> bool:
        """Acknowledge successful processing of an order."""
        pass
