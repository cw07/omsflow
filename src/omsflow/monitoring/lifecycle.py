import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from prometheus_client import Counter, Gauge, Histogram
from structlog import get_logger

from omsflow.core.models import Order, OrderStatus, OrderType
from omsflow.execution.broker import BrokerInterface


logger = get_logger()

# Prometheus metrics
ORDER_PROCESSING_TIME = Histogram(
    "order_processing_seconds",
    "Time spent processing orders",
    ["order_type", "status"]
)
ORDER_STATUS = Gauge(
    "order_status_total",
    "Number of orders by status",
    ["status"]
)
ORDER_ERRORS = Counter(
    "order_errors_total",
    "Number of order processing errors",
    ["error_type"]
)


class OrderLifecycleManager:
    """Manages the lifecycle of orders including monitoring and status updates."""
    
    def __init__(
        self,
        broker: BrokerInterface,
        account: str,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        self.broker = broker
        self.account = account
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.active_orders: Dict[str, Order] = {}
        self._monitoring_tasks: Set[asyncio.Task] = set()

    async def start_monitoring(self) -> None:
        """Start monitoring active orders."""
        for order in self.active_orders.values():
            if order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
                task = asyncio.create_task(self._monitor_order(order))
                self._monitoring_tasks.add(task)
                task.add_done_callback(self._monitoring_tasks.discard)

    async def stop_monitoring(self) -> None:
        """Stop all monitoring tasks."""
        for task in self._monitoring_tasks:
            task.cancel()
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        self._monitoring_tasks.clear()

    async def _monitor_order(self, order: Order) -> None:
        """Monitor a single order's status."""
        retry_count = 0
        last_check = datetime.utcnow()

        while True:
            try:
                # Determine polling interval based on order type
                if order.order_type in [OrderType.TWAP, OrderType.VWAP]:
                    interval = 300  # 5 minutes for TWAP/VWAP
                else:
                    interval = 5  # 5 seconds for other orders

                # Wait for the appropriate interval
                await asyncio.sleep(interval)

                # Check order status
                result = await self.broker.get_order_status(
                    str(order.order_id),
                    self.account
                )

                if not result.success:
                    ORDER_ERRORS.labels(error_type="status_check_failed").inc()
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        logger.error(
                            "order_status_check_failed",
                            order_id=str(order.order_id),
                            error=result.error_message
                        )
                        break
                    continue

                # Update order status
                if result.execution_id:
                    order.status = OrderStatus.FILLED
                    ORDER_STATUS.labels(status="filled").inc()
                    break
                elif order.status != result.status:
                    order.status = result.status
                    ORDER_STATUS.labels(status=result.status).inc()

                # Record processing time
                processing_time = (datetime.utcnow() - last_check).total_seconds()
                ORDER_PROCESSING_TIME.labels(
                    order_type=order.order_type,
                    status=order.status
                ).observe(processing_time)

                last_check = datetime.utcnow()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "order_monitoring_error",
                    order_id=str(order.order_id),
                    error=str(e)
                )
                ORDER_ERRORS.labels(error_type="monitoring_error").inc()
                break

    async def add_order(self, order: Order) -> None:
        """Add a new order to monitoring."""
        self.active_orders[str(order.order_id)] = order
        ORDER_STATUS.labels(status=order.status).inc()
        
        if order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
            task = asyncio.create_task(self._monitor_order(order))
            self._monitoring_tasks.add(task)
            task.add_done_callback(self._monitoring_tasks.discard)

    async def remove_order(self, order_id: str) -> None:
        """Remove an order from monitoring."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            ORDER_STATUS.labels(status=order.status).dec()
            del self.active_orders[order_id]

    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
        execution_id: Optional[str] = None
    ) -> None:
        """Update the status of a monitored order."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            ORDER_STATUS.labels(status=order.status).dec()
            order.status = new_status
            if execution_id:
                order.metadata["execution_id"] = execution_id
            ORDER_STATUS.labels(status=new_status).inc() 