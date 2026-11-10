"""
Models module for domain layer.
Re-exports enumerations and entities for clean imports across the application.
"""

from .enums import (
    Amenity,
    BookingStatus,
    LoyaltyTier,
    RoomStatus,
    RoomType,
    ServiceType,
    UserRole,
)
from .entities import (
    AdditionalService,
    Booking,
    Room,
    User,
)

__all__ = [
    "RoomType",
    "RoomStatus",
    "Amenity",
    "UserRole",
    "LoyaltyTier",
    "BookingStatus",
    "ServiceType",
    "User",
    "AdditionalService",
    "Room",
    "Booking",
]
