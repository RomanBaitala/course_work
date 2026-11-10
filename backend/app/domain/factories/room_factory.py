"""
Фабрики для створення номерного фонду готелю.

[GoF Pattern: Factory Method / Породжувальний патерн]
Інкапсулює бізнес-правила створення готельних номерів різних категорій
(Економ, Стандарт, Люкс) із відповідним набором зручностей, місткістю та базовими тарифами.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
import uuid

from app.domain.models.entities import Room
from app.domain.models.enums import Amenity, RoomStatus, RoomType


class EconomyRoom(Room):
    """
    Конкретний продукт: Номер категорії 'Економ'.
    Призначений для 1–2 гостей, містить базовий набір зручностей за доступною ціною.
    """
    DEFAULT_PRICE: float = 650.0
    DEFAULT_CAPACITY: int = 1

    def __init__(
        self,
        room_number: str,
        base_price_per_night: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        status: RoomStatus = RoomStatus.AVAILABLE,
        photo_urls: Optional[List[str]] = None,
        id: Optional[str] = None,
    ):
        base_amenities = amenities if amenities is not None else {
            Amenity.WIFI,
            Amenity.TV,
        }
        super().__init__(
            id=id or str(uuid.uuid4()),
            room_number=room_number,
            room_type=RoomType.ECONOMY,
            base_price_per_night=base_price_per_night if base_price_per_night is not None else self.DEFAULT_PRICE,
            capacity=capacity if capacity is not None else self.DEFAULT_CAPACITY,
            description=description or "Затишний одномісний або двомісний номер економ-класу з базовими зручностями.",
            amenities=base_amenities,
            status=status,
            photo_urls=photo_urls or ["/static/images/rooms/economy.jpg"],
        )


class StandardRoom(Room):
    """
    Конкретний продукт: Номер категорії 'Стандарт'.
    Оптимальний вибір для 2–3 гостей, включає кондиціонер, робочий стіл та сейф.
    """
    DEFAULT_PRICE: float = 1200.0
    DEFAULT_CAPACITY: int = 2

    def __init__(
        self,
        room_number: str,
        base_price_per_night: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        status: RoomStatus = RoomStatus.AVAILABLE,
        photo_urls: Optional[List[str]] = None,
        id: Optional[str] = None,
    ):
        base_amenities = amenities if amenities is not None else {
            Amenity.WIFI,
            Amenity.TV,
            Amenity.AIR_CONDITIONING,
            Amenity.SAFE,
            Amenity.WORK_DESK,
            Amenity.CITY_VIEW,
        }
        super().__init__(
            id=id or str(uuid.uuid4()),
            room_number=room_number,
            room_type=RoomType.STANDARD,
            base_price_per_night=base_price_per_night if base_price_per_night is not None else self.DEFAULT_PRICE,
            capacity=capacity if capacity is not None else self.DEFAULT_CAPACITY,
            description=description or "Зручний двомісний номер стандарту з кондиціонером та робочою зоною.",
            amenities=base_amenities,
            status=status,
            photo_urls=photo_urls or ["/static/images/rooms/standard.jpg"],
        )


class DeluxeRoom(Room):
    """
    Конкретний продукт: Номер категорії 'Люкс'.
    Преміальні апартаменти на 2–4 особи з балконом, джакузі, міні-баром та видом на гори.
    """
    DEFAULT_PRICE: float = 2500.0
    DEFAULT_CAPACITY: int = 3

    def __init__(
        self,
        room_number: str,
        base_price_per_night: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        status: RoomStatus = RoomStatus.AVAILABLE,
        photo_urls: Optional[List[str]] = None,
        id: Optional[str] = None,
    ):
        base_amenities = amenities if amenities is not None else {
            Amenity.WIFI,
            Amenity.TV,
            Amenity.AIR_CONDITIONING,
            Amenity.SAFE,
            Amenity.WORK_DESK,
            Amenity.BALCONY,
            Amenity.MINI_BAR,
            Amenity.JACUZZI,
            Amenity.MOUNTAIN_VIEW,
        }
        super().__init__(
            id=id or str(uuid.uuid4()),
            room_number=room_number,
            room_type=RoomType.DELUXE,
            base_price_per_night=base_price_per_night if base_price_per_night is not None else self.DEFAULT_PRICE,
            capacity=capacity if capacity is not None else self.DEFAULT_CAPACITY,
            description=description or "Просторий люкс із джакузі, міні-баром, балконом та мальовничим краєвидом.",
            amenities=base_amenities,
            status=status,
            photo_urls=photo_urls or ["/static/images/rooms/deluxe.jpg"],
        )


class RoomFactory(ABC):
    """
    Абстрактний творець (Creator) у патерні Factory Method.
    Декларує фабричний метод, що повертає об'єкт класу Room.
    """

    @abstractmethod
    def create_room(
        self,
        room_number: str,
        base_price: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        **kwargs,
    ) -> Room:
        """Фабричний метод створення конкретного екземпляра готельного номера."""
        pass


class EconomyRoomFactory(RoomFactory):
    """Конкретний творець для створення номерів категорії 'Економ'."""

    def create_room(
        self,
        room_number: str,
        base_price: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        **kwargs,
    ) -> Room:
        return EconomyRoom(
            room_number=room_number,
            base_price_per_night=base_price,
            capacity=capacity,
            description=description,
            amenities=amenities,
            **kwargs,
        )


class StandardRoomFactory(RoomFactory):
    """Конкретний творець для створення номерів категорії 'Стандарт'."""

    def create_room(
        self,
        room_number: str,
        base_price: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        **kwargs,
    ) -> Room:
        return StandardRoom(
            room_number=room_number,
            base_price_per_night=base_price,
            capacity=capacity,
            description=description,
            amenities=amenities,
            **kwargs,
        )


class DeluxeRoomFactory(RoomFactory):
    """Конкретний творець для створення номерів категорії 'Люкс'."""

    def create_room(
        self,
        room_number: str,
        base_price: Optional[float] = None,
        capacity: Optional[int] = None,
        description: str = "",
        amenities: Optional[Set[Amenity]] = None,
        **kwargs,
    ) -> Room:
        return DeluxeRoom(
            room_number=room_number,
            base_price_per_night=base_price,
            capacity=capacity,
            description=description,
            amenities=amenities,
            **kwargs,
        )


class RoomFactoryProvider:
    """
    Провайдер/Реєстр конкретних фабрик (Factory Provider / Dispatcher).
    Дозволяє клієнтському коду створювати номери потрібного типу за допомогою enum RoomType,
    не прив'язуючись до конкретних класів фабрик.
    """
    _factories: Dict[RoomType, RoomFactory] = {
        RoomType.ECONOMY: EconomyRoomFactory(),
        RoomType.STANDARD: StandardRoomFactory(),
        RoomType.DELUXE: DeluxeRoomFactory(),
    }

    @classmethod
    def get_factory(cls, room_type: RoomType) -> RoomFactory:
        """Отримує фабрику за категорією номера."""
        factory = cls._factories.get(room_type)
        if not factory:
            raise ValueError(f"Не підтримується фабрика для категорії номера: '{room_type}'")
        return factory

    @classmethod
    def create_room(
        cls,
        room_type: RoomType,
        room_number: str,
        base_price: Optional[float] = None,
        capacity: Optional[int] = None,
        **kwargs,
    ) -> Room:
        """Зручний статичний метод швидкого створення номера через відповідну фабрику."""
        factory = cls.get_factory(room_type)
        return factory.create_room(
            room_number=room_number,
            base_price=base_price,
            capacity=capacity,
            **kwargs,
        )
