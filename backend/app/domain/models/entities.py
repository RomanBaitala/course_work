"""
Доменні сутності предметної області "Система управління готелем".
Містять бізнес-правила, стан та валідацію ключових понять системи.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Set
import uuid

from .enums import (
    Amenity,
    BookingStatus,
    LoyaltyTier,
    RoomStatus,
    RoomType,
    ServiceType,
    UserRole,
)


@dataclass
class User:
    """
    Сутність користувача системи (клієнт готелю або адміністратор).
    Підтримує накопичення бонусних балів та програму лояльності.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str = ""
    email: str = ""
    phone: str = ""
    role: UserRole = UserRole.CLIENT
    loyalty_tier: LoyaltyTier = LoyaltyTier.STANDARD
    bonus_points: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def get_discount_rate(self) -> float:
        """Повертає фіксовану знижку згідно з рівнем лояльності."""
        rates = {
            LoyaltyTier.STANDARD: 0.0,
            LoyaltyTier.SILVER: 0.05,
            LoyaltyTier.GOLD: 0.10,
            LoyaltyTier.PLATINUM: 0.15,
        }
        return rates.get(self.loyalty_tier, 0.0)

    def get_cashback_rate(self) -> float:
        """Повертає відсоток нарахування бонусів за проживання."""
        cashbacks = {
            LoyaltyTier.STANDARD: 0.03,
            LoyaltyTier.SILVER: 0.05,
            LoyaltyTier.GOLD: 0.07,
            LoyaltyTier.PLATINUM: 0.10,
        }
        return cashbacks.get(self.loyalty_tier, 0.03)

    def add_bonus_points(self, points: float) -> None:
        """Нараховує бонусні бали клієнту."""
        if points < 0:
            raise ValueError("Кількість бонусів для нарахування не може бути від'ємною.")
        self.bonus_points += round(points, 2)

    def deduct_bonus_points(self, points_to_use: float) -> float:
        """
        Списує бонусні бали для оплати.
        Повертає фактично списану кількість балів (не більше за наявні).
        """
        if points_to_use < 0:
            raise ValueError("Кількість бонусів для списання не може бути від'ємною.")
        actual_deduction = min(self.bonus_points, points_to_use)
        self.bonus_points -= actual_deduction
        self.bonus_points = round(self.bonus_points, 2)
        return actual_deduction


@dataclass
class AdditionalService:
    """
    Сутність додаткової послуги готелю (харчування, трансфер, SPA).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    service_type: ServiceType = ServiceType.MEAL
    price: float = 0.0
    description: str = ""

    def __post_init__(self):
        if self.price < 0:
            raise ValueError("Ціна додаткової послуги не може бути від'ємною.")


@dataclass
class Room:
    """
    Базова сутність готельного номера.
    Містить інформацію про категорію, місткість, зручності та ціну.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    room_number: str = ""
    room_type: RoomType = RoomType.STANDARD
    base_price_per_night: float = 0.0
    capacity: int = 2
    description: str = ""
    amenities: Set[Amenity] = field(default_factory=set)
    status: RoomStatus = RoomStatus.AVAILABLE
    photo_urls: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.base_price_per_night < 0:
            raise ValueError("Базова ціна за добу не може бути від'ємною.")
        if self.capacity <= 0:
            raise ValueError("Місткість номера повинна бути більшою за 0.")

    def is_available(self) -> bool:
        """Перевіряє, чи вільний номер для бронювання."""
        return self.status == RoomStatus.AVAILABLE

    def has_amenity(self, amenity: Amenity) -> bool:
        """Перевіряє наявність конкретної зручності в номері."""
        return amenity in self.amenities


@dataclass
class Booking:
    """
    Сутність бронювання номера клієнтом.
    Зв'язує гостя, номер, період перебування та додаткові послуги.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    guest: User = field(default_factory=User)
    room: Room = field(default_factory=Room)
    check_in_date: date = field(default_factory=date.today)
    check_out_date: date = field(default_factory=date.today)
    services: List[AdditionalService] = field(default_factory=list)
    status: BookingStatus = BookingStatus.CREATED
    total_price: float = 0.0
    used_bonus_points: float = 0.0
    earned_bonus_points: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Дата виїзду (check-out) має бути пізнішою за дату заїзду (check-in).")

    @property
    def nights_count(self) -> int:
        """Розраховує кількість ночей перебування."""
        return (self.check_out_date - self.check_in_date).days
