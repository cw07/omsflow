from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from omsflow.core.models import Order, OrderExecutionResult
from omsflow.execution.fix_generator import FIXMessageGenerator


class BrokerInterface(ABC):
    """Abstract base class for broker interfaces."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the broker."""
        pass

    @abstractmethod
    async def submit_order(
        self,
        order: Order,
        account: str,
        broker_refdata: Dict[str, Any]
    ) -> OrderExecutionResult:
        """Submit a new order to the broker."""
        pass

    @abstractmethod
    async def cancel_order(
        self,
        order: Order,
        account: str
    ) -> OrderExecutionResult:
        """Cancel an existing order."""
        pass

    @abstractmethod
    async def replace_order(
        self,
        order: Order,
        account: str,
        new_price: Optional[float] = None,
        new_quantity: Optional[float] = None
    ) -> OrderExecutionResult:
        """Replace an existing order with new parameters."""
        pass

    @abstractmethod
    async def get_order_status(
        self,
        order_id: str,
        account: str
    ) -> OrderExecutionResult:
        """Get the current status of an order."""
        pass


class PhoenixBroker(BrokerInterface):
    """Phoenix broker implementation."""
    
    def __init__(
        self,
        sender_comp_id: str,
        target_comp_id: str,
        fix_config_path: str,
        account: str
    ):
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.fix_config_path = fix_config_path
        self.account = account
        self.fix_generator = FIXMessageGenerator(sender_comp_id, target_comp_id)
        self._session = None
        self._initiator = None

    async def connect(self) -> None:
        """Establish FIX connection to Phoenix."""
        try:
            settings = qf.SessionSettings(self.fix_config_path)
            store_factory = qf.FileStoreFactory(settings)
            log_factory = qf.FileLogFactory(settings)
            self._initiator = qf.SocketInitiator(
                self,
                store_factory,
                settings,
                log_factory
            )
            self._initiator.start()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Phoenix: {str(e)}")

    async def disconnect(self) -> None:
        """Close FIX connection to Phoenix."""
        if self._initiator:
            self._initiator.stop()
            self._initiator = None

    async def submit_order(
        self,
        order: Order,
        account: str,
        broker_refdata: Dict[str, Any]
    ) -> OrderExecutionResult:
        """Submit a new order to Phoenix."""
        try:
            msg = self.fix_generator.create_new_order(order, account, broker_refdata)
            self._session.send(msg)
            return OrderExecutionResult(
                success=True,
                order_id=order.order_id,
                broker_order_id=order.client_order_id
            )
        except Exception as e:
            return OrderExecutionResult(
                success=False,
                order_id=order.order_id,
                error_message=str(e)
            )

    async def cancel_order(
        self,
        order: Order,
        account: str
    ) -> OrderExecutionResult:
        """Cancel an existing order in Phoenix."""
        try:
            msg = self.fix_generator.create_cancel_order(
                order,
                order.client_order_id,
                account
            )
            self._session.send(msg)
            return OrderExecutionResult(
                success=True,
                order_id=order.order_id,
                broker_order_id=order.client_order_id
            )
        except Exception as e:
            return OrderExecutionResult(
                success=False,
                order_id=order.order_id,
                error_message=str(e)
            )

    async def replace_order(
        self,
        order: Order,
        account: str,
        new_price: Optional[float] = None,
        new_quantity: Optional[float] = None
    ) -> OrderExecutionResult:
        """Replace an existing order in Phoenix."""
        try:
            msg = self.fix_generator.create_replace_order(
                order,
                order.client_order_id,
                account,
                new_price,
                new_quantity
            )
            self._session.send(msg)
            return OrderExecutionResult(
                success=True,
                order_id=order.order_id,
                broker_order_id=order.client_order_id
            )
        except Exception as e:
            return OrderExecutionResult(
                success=False,
                order_id=order.order_id,
                error_message=str(e)
            )

    async def get_order_status(
        self,
        order_id: str,
        account: str
    ) -> OrderExecutionResult:
        """Get the current status of an order from Phoenix."""
        try:
            # Implement order status request using FIX
            msg = self.fix_generator._create_header("H")  # Order Status Request
            msg.setField(qf.ClOrdID(order_id))
            msg.setField(qf.Account(account))
            self._session.send(msg)
            
            # Note: In a real implementation, you would need to handle the response
            # and map it to an OrderExecutionResult
            return OrderExecutionResult(
                success=True,
                order_id=order_id
            )
        except Exception as e:
            return OrderExecutionResult(
                success=False,
                order_id=order_id,
                error_message=str(e)
            ) 