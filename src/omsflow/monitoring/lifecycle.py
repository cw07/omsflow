import logging
import asyncio
import datetime as dt
from typing import Any, Dict, List, Optional, Set

from prometheus_client import Counter, Gauge, Histogram

from omsflow.models.order import Order, OrderStatus, OrderType
from omsflow.execution.base import ExecutionInterface

_log = logging.getLogger(__name__)

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
            exec_system: ExecutionInterface,
            max_retries: int = 3,
            retry_delay: int = 5
    ):
        self.exec_system = exec_system
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
        self._monitoring_tasks.clean()

    async def _monitor_order(self, order: Order) -> None:
        """Monitor a single order's status."""
        retry_count = 0
        last_check = dt.datetime.now()

        while True:
            try:
                if order.order_type in [OrderType.TWAP, OrderType.VWAP]:
                    interval = 300  # 5 minutes for TWAP/VWAP
                else:
                    interval = 5  # 5 seconds for other orders

                # Wait for the appropriate interval
                await asyncio.sleep(interval)

                # Check order status
                result = await self.exec_system.get_order_status(str(order.client_order_id))

                if not result.success:
                    ORDER_ERRORS.labels(error_type="status_check_failed").inc()
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        _log.error(
                            "order_status_check_failed",
                        )
                        break
                    continue

                # Convert external status to internal status
                internal_status = StatusMapper.to_internal_status(result.status)

                # Update order status
                if result.execution_id:
                    order.status = OrderStatus.FILLED
                    ORDER_STATUS.labels(status="filled").inc()
                    break
                elif order.status != internal_status:
                    order.status = internal_status
                    ORDER_STATUS.labels(status=internal_status.value).inc()

                # Record processing time
                processing_time = (dt.datetime.now() - last_check).total_seconds()
                ORDER_PROCESSING_TIME.labels(
                    order_type=order.order_type,
                    status=order.status.value
                ).observe(processing_time)

                last_check = dt.datetime.now()

            except asyncio.CancelledError:
                break
            except Exception as e:
                _log.error("order_monitoring_error")
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
