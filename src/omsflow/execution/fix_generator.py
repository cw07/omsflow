from datetime import datetime
from typing import Any, Dict, Optional

import quickfix as qf

from omsflow.core.models import Order, OrderType, SecurityType, TimeInForce


class FIXMessageGenerator:
    """Generates FIX messages for order execution."""
    
    def __init__(self, sender_comp_id: str, target_comp_id: str):
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id

    def _create_header(self, msg_type: str) -> qf.Message:
        """Create a FIX message header."""
        header = qf.Message()
        header.getHeader().setField(qf.MsgType(msg_type))
        header.getHeader().setField(qf.SenderCompID(self.sender_comp_id))
        header.getHeader().setField(qf.TargetCompID(self.target_comp_id))
        header.getHeader().setField(qf.SendingTime(datetime.utcnow()))
        return header

    def _map_order_type(self, order_type: OrderType) -> str:
        """Map internal order type to FIX order type."""
        mapping = {
            OrderType.MARKET: "2",  # Market
            OrderType.LIMIT: "2",   # Limit
            OrderType.TWAP: "U",    # TWAP
            OrderType.VWAP: "V",    # VWAP
        }
        return mapping.get(order_type, "2")

    def _map_time_in_force(self, tif: TimeInForce) -> str:
        """Map internal time in force to FIX time in force."""
        mapping = {
            TimeInForce.DAY: "0",   # Day
            TimeInForce.GTC: "1",   # Good Till Cancel
            TimeInForce.IOC: "3",   # Immediate or Cancel
            TimeInForce.FOK: "4",   # Fill or Kill
        }
        return mapping.get(tif, "0")

    def _map_security_type(self, security_type: SecurityType) -> str:
        """Map internal security type to FIX security type."""
        mapping = {
            SecurityType.EQUITY: "CS",  # Common Stock
            SecurityType.FUTURE: "FUT", # Future
            SecurityType.OPTION: "OPT", # Option
            SecurityType.FOREX: "CURR", # Currency
        }
        return mapping.get(security_type, "CS")

    def create_new_order(
        self,
        order: Order,
        account: str,
        broker_refdata: Dict[str, Any]
    ) -> qf.Message:
        """Create a new order FIX message."""
        msg = self._create_header("D")  # New Order Single

        # Required fields
        msg.setField(qf.ClOrdID(order.client_order_id))
        msg.setField(qf.Symbol(order.symbol))
        msg.setField(qf.Side("1" if order.side == "BUY" else "2"))
        msg.setField(qf.OrderQty(order.quantity))
        msg.setField(qf.OrdType(self._map_order_type(order.order_type)))
        msg.setField(qf.TimeInForce(self._map_time_in_force(order.time_in_force)))
        msg.setField(qf.Account(account))
        msg.setField(qf.SecurityType(self._map_security_type(order.security_type)))

        # Optional fields
        if order.price:
            msg.setField(qf.Price(order.price))

        # Add broker-specific fields from reference data
        for field, value in broker_refdata.items():
            if isinstance(value, (str, int, float)):
                msg.setField(qf.StringField(int(field), str(value)))

        return msg

    def create_cancel_order(
        self,
        order: Order,
        orig_cl_ord_id: str,
        account: str
    ) -> qf.Message:
        """Create a cancel order FIX message."""
        msg = self._create_header("F")  # Order Cancel Request

        msg.setField(qf.ClOrdID(order.client_order_id))
        msg.setField(qf.OrigClOrdID(orig_cl_ord_id))
        msg.setField(qf.Symbol(order.symbol))
        msg.setField(qf.Side("1" if order.side == "BUY" else "2"))
        msg.setField(qf.OrderQty(order.quantity))
        msg.setField(qf.Account(account))

        return msg

    def create_replace_order(
        self,
        order: Order,
        orig_cl_ord_id: str,
        account: str,
        new_price: Optional[float] = None,
        new_quantity: Optional[float] = None
    ) -> qf.Message:
        """Create a replace order FIX message."""
        msg = self._create_header("G")  # Order Cancel/Replace Request

        msg.setField(qf.ClOrdID(order.client_order_id))
        msg.setField(qf.OrigClOrdID(orig_cl_ord_id))
        msg.setField(qf.Symbol(order.symbol))
        msg.setField(qf.Side("1" if order.side == "BUY" else "2"))
        msg.setField(qf.OrderQty(new_quantity or order.quantity))
        msg.setField(qf.OrdType(self._map_order_type(order.order_type)))
        msg.setField(qf.TimeInForce(self._map_time_in_force(order.time_in_force)))
        msg.setField(qf.Account(account))

        if new_price is not None:
            msg.setField(qf.Price(new_price))
        elif order.price:
            msg.setField(qf.Price(order.price))

        return msg 