from typing import AsyncIterator, Any

from chrono.backends.db import chrono_db
from omsflow.ordersources.base import OrderSource


class SQLOrderSource(OrderSource):
    """Base class for SQL - based order sources."""

    def __init__(self, database):
        if database == "chrono":
            self.database = chrono_db
        else:
            raise NotImplementedError(f"{database} not supported for database order source")

    async def execute_query(self, query: str, params: dict) -> list[dict]:
        """Execute a SQL query and return results."""
        pass

    async def stream_orders(self) -> AsyncIterator[Any]:
        pass

    async def acknowledge_order(self, order_id: str) -> bool:
        pass
