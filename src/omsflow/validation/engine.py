from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from omsflow.models.order import Order, OrderValidationResult


class ValidationRule(ABC):
    """Abstract base class for order validation rules."""
    
    @abstractmethod
    async def validate(self, order: Order, context: Dict[str, Any]) -> OrderValidationResult:
        """Validate an order against this rule."""
        pass


class PriceValidationRule(ValidationRule):
    """Validates order prices against market data and limits."""
    
    def __init__(self, max_price_deviation: float = 0.05):
        self.max_price_deviation = max_price_deviation

    async def validate(self, order: Order, context: Dict[str, Any]) -> OrderValidationResult:
        if order.order_type == "MARKET":
            return OrderValidationResult(is_valid=True)

        market_price = context.get("market_price")
        if not market_price:
            return OrderValidationResult(
                is_valid=False,
                errors=["Market price not available for validation"]
            )

        if not order.price:
            return OrderValidationResult(
                is_valid=False,
                errors=["Price is required for limit orders"]
            )

        deviation = abs(order.price - market_price) / market_price
        if deviation > self.max_price_deviation:
            return OrderValidationResult(
                is_valid=False,
                errors=[f"Price deviation {deviation:.2%} exceeds maximum {self.max_price_deviation:.2%}"]
            )

        return OrderValidationResult(is_valid=True)


class PositionLimitRule(ValidationRule):
    """Validates orders against position limits."""
    
    def __init__(self, max_position_value: float):
        self.max_position_value = max_position_value

    async def validate(self, order: Order, context: Dict[str, Any]) -> OrderValidationResult:
        current_position = context.get("current_position", 0)
        order_value = order.quantity * (order.price or context.get("market_price", 0))

        if current_position + order_value > self.max_position_value:
            return OrderValidationResult(
                is_valid=False,
                errors=[
                    f"Order value {order_value:.2f} would exceed position limit "
                    f"{self.max_position_value:.2f}"
                ]
            )

        return OrderValidationResult(is_valid=True)


class ValidationEngine:
    """Main validation engine that applies multiple rules to orders."""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule to the engine."""
        self.rules.append(rule)

    async def validate_order(
        self, order: Order, context: Optional[Dict[str, Any]] = None
    ) -> OrderValidationResult:
        """Validate an order against all registered rules."""
        context = context or {}
        all_errors: List[str] = []
        all_warnings: List[str] = []

        for rule in self.rules:
            result = await rule.validate(order, context)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        return OrderValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        ) 