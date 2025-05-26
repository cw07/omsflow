import asyncio
from typing import Any, Dict, Optional, Type

from omsflow.models.order import Order, OrderExecutionResult, OrderValidationResult
from omsflow.execution.base import ExecutionInterface
from omsflow.monitoring.lifecycle import OrderLifecycleManager
from omsflow.ordersources.base import OrderSource
from omsflow.validation.engine import ValidationEngine


class OrderManagementSystem:
    """Main Order Management System that coordinates all components."""

    def __init__(
            self,
            order_source: OrderSource,
            exec_client: ExecutionInterface,
            validation_engine: ValidationEngine,
    ):
        self.order_source: OrderSource = order_source
        self.exec_client: ExecutionInterface = exec_client
        self.validation_engine = validation_engine
        self.lifecycle_manager = OrderLifecycleManager(exec_client)
        self._running = False
        self._order_processor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the Order Management System."""
        if self._running:
            return

        self._running = True

        # Connect to order source and broker
        await self.order_source.connect()
        await self.exec_client.connect()

        # Start monitoring
        await self.lifecycle_manager.start_monitoring()

        # Start order processing
        self._order_processor_task = asyncio.create_task(self._process_orders())

    async def stop(self) -> None:
        """Stop the Order Management System."""
        if not self._running:
            return

        self._running = False

        # Stop order processing
        if self._order_processor_task:
            self._order_processor_task.cancel()
            try:
                await self._order_processor_task
            except asyncio.CancelledError:
                pass

        # Stop monitoring
        await self.lifecycle_manager.stop_monitoring()

        # Disconnect from order source and broker
        await self.order_source.disconnect()
        await self.exec_client.disconnect()

    async def _process_orders(self) -> None:
        """Process incoming orders from the order source."""
        try:
            async for order in self.order_source.stream_orders():
                try:
                    # Validate order
                    validation_result = await self.validation_engine.validate_order(order)

                    if not validation_result.is_valid:
                        # Handle validation errors
                        for error in validation_result.errors:
                            # Log error and potentially send to dead letter queue
                            continue

                    # Submit order to broker
                    execution_result = await self.exec_client.submit_order(
                        order
                    )

                    if execution_result.success:
                        # Add order to lifecycle management
                        await self.lifecycle_manager.add_order(order)

                        # Acknowledge order in source
                        await self.order_source.acknowledge_order(str(order.order_id))
                    else:
                        # Handle execution errors
                        # Log error and potentially retry
                        continue
                except Exception as e:
                    # Handle unexpected errors
                    # Log error and potentially send to dead letter queue
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Handle fatal errors
            # Log error and potentially trigger system shutdown
            pass

    async def submit_order(self, order: Order) -> OrderExecutionResult:
        # Submit order to broker
        execution_result = await self.exec_client.submit_order(
            order
        )

        if execution_result.success:
            # Add order to lifecycle management
            await self.lifecycle_manager.add_order(order)

        return execution_result

    async def cancel_order(self, order_id: str) -> OrderExecutionResult:
        """Cancel an existing order."""
        # Get order from lifecycle manager
        order = self.lifecycle_manager.active_orders.get(order_id)
        if not order:
            return OrderExecutionResult(
                success=False,
                order_id=order_id,
                error_message="Order not found"
            )

        # Cancel order through broker
        execution_result = await self.exec_client.cancel_order(order)

        if execution_result.success:
            # Remove order from lifecycle management
            await self.lifecycle_manager.remove_order(order_id)

        return execution_result
