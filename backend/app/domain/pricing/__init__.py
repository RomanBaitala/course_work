"""
Pricing package containing Decorators and Strategies for price calculation.
"""

from .service_decorator import (
    BaseRoomStay,
    OneTimeServiceDecorator,
    PerNightServiceDecorator,
    PricedItem,
    ServiceDecorator,
    build_priced_stay,
    decorate_with_service,
)
from .pricing_strategy import (
    LongStayDiscountStrategy,
    LoyaltyPricingStrategy,
    PricingCalculatorContext,
    PricingStrategy,
    StandardPricingStrategy,
    WeekendSurchargeStrategy,
)

__all__ = [
    # GoF Decorator
    "PricedItem",
    "BaseRoomStay",
    "ServiceDecorator",
    "PerNightServiceDecorator",
    "OneTimeServiceDecorator",
    "decorate_with_service",
    "build_priced_stay",
    # GoF Strategy
    "PricingStrategy",
    "StandardPricingStrategy",
    "LongStayDiscountStrategy",
    "LoyaltyPricingStrategy",
    "WeekendSurchargeStrategy",
    "PricingCalculatorContext",
]
