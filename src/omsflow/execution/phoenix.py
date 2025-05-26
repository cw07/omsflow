import time
import logging
import requests
from typing import Dict, Any

from omsflow.execution.base import ExecutionInterface
from omsflow.models.order import Order, OrderExecutionResult

_log = logging.getLogger(__name__)


class PhxExecution(ExecutionInterface):
    def __init__(self, client):
        self.client = client

    def submit_order(
            self,
            order: Order
    ) -> OrderExecutionResult:
        payload = {}
        self.client.submit_order(payload)

    def cancel_order(
            self,
            order: Order,
    ) -> OrderExecutionResult:
        client_order_id = order.client_order_id
        self.client.cancel_order(client_order_id)

    def get_order_status(self,
                         order: Order
                         ):
        client_order_id = order.client_order_id
        self.client.get_order_status_by_id(client_order_id)
