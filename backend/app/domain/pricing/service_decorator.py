"""
Декоратори додаткових послуг готелю.

[GoF Pattern: Decorator / Структурний патерн]
Дозволяє динамічно додавати нові платні опції (сніданок, SPA, трансфер)
до базової вартості проживання в номері без зміни самого класу Room чи Booking,
формуючи деталізований опис вартості та чека.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.entities import AdditionalService, Room
from app.domain.models.enums import ServiceType


class PricedItem(ABC):
    """
    Базовий компонент (Component) у патерні Decorator.
    Визначає інтерфейс для розрахунку вартості та отримання опису елементів замовлення.
    """

    @abstractmethod
    def calculate_cost(self) -> float:
        """Повертає загальну вартість елемента замовлення."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Повертає текстовий опис складових замовлення."""
        pass


class BaseRoomStay(PricedItem):
    """
    Конкретний компонент (Concrete Component).
    Базове проживання в номері на визначену кількість діб без додаткових послуг.
    """

    def __init__(self, room: Room, nights: int):
        if nights <= 0:
            raise ValueError("Кількість діб має бути більшою за 0.")
        self.room = room
        self.nights = nights

    def calculate_cost(self) -> float:
        """Вартість номера за вказану кількість діб."""
        return round(self.room.base_price_per_night * self.nights, 2)

    def get_description(self) -> str:
        return (
            f"Проживання в номері {self.room.room_number} "
            f"({self.room.room_type.value}) на {self.nights} діб: {self.calculate_cost()} грн"
        )


class ServiceDecorator(PricedItem, ABC):
    """
    Базовий декоратор (Base Decorator).
    Містить посилання на об'єкт PricedItem і делегує йому базові виклики.
    """

    def __init__(self, wrappee: PricedItem):
        self._wrappee = wrappee

    @property
    def wrappee(self) -> PricedItem:
        return self._wrappee

    def calculate_cost(self) -> float:
        return self._wrappee.calculate_cost()

    def get_description(self) -> str:
        return self._wrappee.get_description()


class BreakfastDecorator(ServiceDecorator):
    """
    Конкретний декоратор: додає вартість сніданків.
    Розраховується як щоденне харчування на весь термін перебування.
    """

    def __init__(self, wrappee: PricedItem, price_per_day: float = 250.0, guests_count: int = 1):
        super().__init__(wrappee)
        if price_per_day < 0 or guests_count <= 0:
            raise ValueError("Ціна сніданку та кількість гостей повинні бути коректними.")
        self.price_per_day = price_per_day
        self.guests_count = guests_count

    def _get_service_cost(self) -> float:
        # Якщо вкладений компонент — проживання в номері, беремо його кількість ночей
        nights = getattr(self._wrappee, "nights", 1)
        return round(self.price_per_day * self.guests_count * nights, 2)

    def calculate_cost(self) -> float:
        return round(self._wrappee.calculate_cost() + self._get_service_cost(), 2)

    def get_description(self) -> str:
        cost = self._get_service_cost()
        return f"{self._wrappee.get_description()} + Сніданок (шведський стіл, {self.guests_count} ос.): {cost} грн"


class TransferDecorator(ServiceDecorator):
    """
    Конкретний декоратор: додає вартість трансферу (фіксована разова послуга).
    """

    def __init__(self, wrappee: PricedItem, transfer_price: float = 400.0, route: str = "Аеропорт -> Готель"):
        super().__init__(wrappee)
        if transfer_price < 0:
            raise ValueError("Ціна трансферу не може бути від'ємною.")
        self.transfer_price = transfer_price
        self.route = route

    def calculate_cost(self) -> float:
        return round(self._wrappee.calculate_cost() + self.transfer_price, 2)

    def get_description(self) -> str:
        return f"{self._wrappee.get_description()} + Трансфер ({self.route}): {self.transfer_price} грн"


class SpaPackageDecorator(ServiceDecorator):
    """
    Конкретний декоратор: додає безлімітний або разовий доступ до SPA-зони.
    """

    def __init__(self, wrappee: PricedItem, spa_price: float = 700.0, package_name: str = "Relax & Thermal SPA"):
        super().__init__(wrappee)
        if spa_price < 0:
            raise ValueError("Ціна SPA-пакету не може бути від'ємною.")
        self.spa_price = spa_price
        self.package_name = package_name

    def calculate_cost(self) -> float:
        return round(self._wrappee.calculate_cost() + self.spa_price, 2)

    def get_description(self) -> str:
        return f"{self._wrappee.get_description()} + SPA ({self.package_name}): {self.spa_price} грн"


class CustomServiceDecorator(ServiceDecorator):
    """
    Універсальний конкретний декоратор для обгортання будь-якої сутності AdditionalService.
    """

    def __init__(self, wrappee: PricedItem, service: AdditionalService):
        super().__init__(wrappee)
        self.service = service

    def calculate_cost(self) -> float:
        return round(self._wrappee.calculate_cost() + self.service.price, 2)

    def get_description(self) -> str:
        return f"{self._wrappee.get_description()} + {self.service.name}: {self.service.price} грн"
