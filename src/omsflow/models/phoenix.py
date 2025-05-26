from typing import Dict, ClassVar, Type


class AnotherOrderStatus:
    Accepted = 'Accepted'

class PhxOrderStatus:
    ACCEPTED = 'Accepted'
    CALCULATED = 'Calculated'
    CANCELED = 'Canceled'
    DONE_FOR_DAY = 'DoneForDay'
    EXPIRED = 'Expired'
    FILLED = 'Filled'
    PARTIAL = 'Partial'
    PENDING_CANCEL = 'PendingCancel'
    PENDING_NEW = 'PendingNew'
    PENDING_REPLACE = 'PendingReplace'
    REJECTED = 'Rejected'
    REPLACED = 'Replaced'
    STOPPED = 'Stopped'
    SUSPENDED = 'Suspended'
    Unknown = 'Unknown'


class DefaultOrderStatus:
    """Default order status representation."""
    ACCEPTED = 'Accepted'
    CALCULATED = 'Calculated'
    CANCELED = 'Canceled'
    DONE_FOR_DAY = 'DoneForDay'
    EXPIRED = 'Expired'
    FILLED = 'Filled'
    PARTIAL = 'Partial'
    PENDING_CANCEL = 'PendingCancel'
    PENDING_NEW = 'PendingNew'
    PENDING_REPLACE = 'PendingReplace'
    REJECTED = 'Rejected'
    REPLACED = 'Replaced'
    STOPPED = 'Stopped'

    # System-specific status mappings
    _system_mappings: ClassVar[Dict[str, Type]] = {
        "phoenix": PhxOrderStatus,
    }

    def __new__(cls, system: str) -> Type:
        if system == "phoenix":
            system_status = cls._system_mappings["phoenix"]
            # Create a new class with system-specific constants
            class DynamicOrderStatus:
                ACCEPTED = getattr(system_status, "ACCEPTED", cls.ACCEPTED)
                CANCELED = getattr(system_status, "CANCELED", cls.CANCELED)
                FILLED = getattr(system_status, "FILLED", cls.FILLED)
                PARTIAL = getattr(system_status, "PARTIAL", cls.PARTIAL)
                PENDING_CANCEL = getattr(system_status, "PENDING_CANCEL", cls.PENDING_CANCEL)
                PENDING_NEW = getattr(system_status, "PENDING_NEW", cls.PENDING_NEW)
                REJECTED = getattr(system_status, "REJECTED", cls.REJECTED)
            return DynamicOrderStatus
        else:
            raise NotImplementedError()




if __name__ == "__main__":
    order_system = "phoenix"
    if order_system == "phoenix":
        OrderStatus = DefaultOrderStatus("phoenix")



