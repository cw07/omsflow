import asyncio
from typing import Any, Dict, Optional, Type

from omsflow.core.models import Order, OrderExecutionResult, OrderValidationResult
from omsflow.execution.broker import BrokerInterface
from omsflow.monitoring.lifecycle import OrderLifecycleManager
from omsflow.sources.base import OrderSource
from omsflow.validation.engine import ValidationEngine


class OrderManagementSystem:
    """Main Order Management System that coordinates all components."""
    
    def __init__(
        self,
        order_source: OrderSource,
        broker: BrokerInterface,
        validation_engine: ValidationEngine,
        account: str,
        broker_refdata: Dict[str, Any]
    ):
        self.order_source = order_source
        self.broker = broker
        self.validation_engine = validation_engine
        self.account = account
        self.broker_refdata = broker_refdata
        self.lifecycle_manager = OrderLifecycleManager(broker, account)
        self._running = False
        self._order_processor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the Order Management System."""
        if self._running:
            return

        self._running = True
        
        # Connect to order source and broker
        await self.order_source.connect()
        await self.broker.connect()
        
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
        await self.broker.disconnect()

    async def _process_orders(self) -> None:
        """Process incoming orders from the order source."""
        try:
            async for order in self.order_source.stream_orders():
                try:
                    # Validate order
                    validation_result = await self.validation_engine.validate_order(
                        order,
                        {"broker_refdata": self.broker_refdata}
                    )

                    if not validation_result.is_valid:
                        # Handle validation errors
                        for error in validation_result.errors:
                            # Log error and potentially send to dead letter queue
                            continue

                    # Submit order to broker
                    execution_result = await self.broker.submit_order(
                        order,
                        self.account,
                        self.broker_refdata
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
        """Submit a single order through the system."""
        # Validate order
        validation_result = await self.validation_engine.validate_order(
            order,
            {"broker_refdata": self.broker_refdata}
        )

        if not validation_result.is_valid:
            return OrderExecutionResult(
                success=False,
                order_id=order.order_id,
                error_message="; ".join(validation_result.errors)
            )

        # Submit order to broker
        execution_result = await self.broker.submit_order(
            order,
            self.account,
            self.broker_refdata
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
        execution_result = await self.broker.cancel_order(order, self.account)

        if execution_result.success:
            # Remove order from lifecycle management
            await self.lifecycle_manager.remove_order(order_id)

        return execution_result

    async def replace_order(
        self,
        order_id: str,
        new_price: Optional[float] = None,
        new_quantity: Optional[float] = None
    ) -> OrderExecutionResult:
        """Replace an existing order with new parameters."""
        # Get order from lifecycle manager
        order = self.lifecycle_manager.active_orders.get(order_id)
        if not order:
            return OrderExecutionResult(
                success=False,
                order_id=order_id,
                error_message="Order not found"
            )

        # Replace order through broker
        execution_result = await self.broker.replace_order(
            order,
            self.account,
            new_price,
            new_quantity
        )

        if execution_result.success:
            # Update order in lifecycle management
            if new_price is not None:
                order.price = new_price
            if new_quantity is not None:
                order.quantity = new_quantity

        return execution_result 