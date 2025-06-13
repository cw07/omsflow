from typing import AsyncIterator, Any, AsyncIterable
import asyncio
from datetime import datetime
from uuid import UUID

from chrono.backends.db import chrono_db
from omsflow.ordersources.base import OrderSource
from omsflow.models.order import Order, OrderType, OrderStatus


class SQLOrderSource(OrderSource):
    """Base class for SQL - based order sources."""

    def __init__(self, database):
        if database == "chrono":
            self.database = chrono_db
        else:
            raise NotImplementedError(f"{database} not supported for database order source")
        self._running = False
        self._poll_interval = 1.0  # seconds between polls
        self._current_batch = []
        self._current_index = 0

    async def connect(self) -> None:
        """Establish connection to the database."""
        # Connection is handled by chrono_db
        self._running = True

    async def disconnect(self) -> None:
        """Close connection to the database."""
        self._running = False

    @property
    def new_orders(self) -> AsyncIterable[Order]:
        """Property that returns an async iterable of new orders."""
        self._current_batch = []
        self._current_index = 0
        return self

    async def execute_query(self, query: str, params: dict) -> list[dict]:
        """Execute a SQL query and return results."""
        if query == "get_pending_orders":
            query = """
                SELECT 
                    order_id,
                    client_order_id,
                    symbol,
                    security_type,
                    side,
                    quantity,
                    order_type,
                    time_in_force,
                    price,
                    created_at,
                    updated_at,
                    metadata
                FROM orders 
                WHERE status = 'PENDING'
                AND processed = false
                ORDER BY created_at ASC
                LIMIT 100
            """
        elif query == "acknowledge_order":
            query = """
                UPDATE orders 
                SET processed = true,
                    updated_at = :updated_at
                WHERE order_id = :order_id
            """
        
        return await self.database.execute_query(query, params)

    def __aiter__(self) -> AsyncIterator[Order]:
        """Initialize async iteration."""
        return self

    async def __anext__(self) -> Order:
        """Get the next order in the stream.
        
        Returns:
            Order: The next order in the stream.
            
        Raises:
            StopAsyncIteration: When there are no more orders to process.
        """
        if not self._running:
            raise StopAsyncIteration

        # If we've exhausted the current batch, fetch a new one
        if self._current_index >= len(self._current_batch):
            try:
                self._current_batch = await self.execute_query("get_pending_orders", {})
                self._current_index = 0
                
                if not self._current_batch:
                    # No new orders, wait before polling again
                    await asyncio.sleep(self._poll_interval)
                    return await self.__anext__()
                    
            except Exception as e:
                print(f"Error polling orders: {str(e)}")
                await asyncio.sleep(self._poll_interval)
                return await self.__anext__()

        try:
            # Get the next row and convert to Order
            row = self._current_batch[self._current_index]
            self._current_index += 1
            
            order = Order(
                order_id=UUID(row['order_id']),
                client_order_id=row['client_order_id'],
                symbol=row['symbol'],
                security_type=row['security_type'],
                side=row['side'],
                quantity=float(row['quantity']),
                order_type=OrderType(row['order_type']),
                time_in_force=row['time_in_force'],
                price=float(row['price']) if row['price'] is not None else None,
                status=OrderStatus.PENDING,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                metadata=row['metadata'] or {}
            )
            
            return order
            
        except Exception as e:
            print(f"Error processing order {row.get('order_id')}: {str(e)}")
            # Skip this order and try the next one
            return await self.__anext__()

    async def acknowledge_order(self, order_id: str) -> bool:
        """Mark an order as processed in the database."""
        try:
            await self.execute_query("acknowledge_order", {
                'order_id': order_id,
                'updated_at': datetime.utcnow()
            })
            return True
        except Exception as e:
            print(f"Error acknowledging order {order_id}: {str(e)}")
            return False
