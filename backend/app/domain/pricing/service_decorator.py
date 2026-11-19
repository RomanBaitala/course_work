"""
Декоратори додаткових послуг готелю.

[GoF Pattern: Decorator / Структурний патерн]
Дозволяє динамічно додавати платні опції (сніданок, SPA, трансфер тощо)
до базової вартості проживання в номері без зміни самого класу Room чи Booking,
формуючи деталізований опис вартості та чека.

Декоратори будуються з послуг, що зберігаються в БД (AdditionalService), тому
ціни задає адміністратор, а не код. Спосіб тарифікації залежить від типу послуги:
  • харчування (MEAL) — за кожну ніч проживання;
  • решта послуг (трансфер, SPA, прибирання, екскурсії) — разово.
"""

from abc import ABC, abstractmethod
from typing import Iterable, List, Tuple

from app.domain.models.entities import AdditionalService, Room
from app.domain.models.enums import ServiceType

# Типи послуг, що тарифікуються за кожну ніч проживання
PER_NIGHT_SERVICE_TYPES = {ServiceType.MEAL}

ReceiptLine = Tuple[str, float]


class PricedItem(ABC):
    """
    Базовий компонент (Component) у патерні Decorator.
    Визначає інтерфейс для розрахунку вартості та отримання опису елементів замовлення.
    """

    @property
    @abstractmethod
    def nights(self) -> int:
        """Кількість ночей проживання (потрібна декораторам з тарифікацією за ніч)."""

    @abstractmethod
    def calculate_cost(self) -> float:
        """Повертає загальну вартість елемента замовлення."""

    @abstractmethod
    def get_receipt_lines(self) -> List[ReceiptLine]:
        """Повертає рядки чека: (назва позиції, вартість)."""

    def get_description(self) -> str:
        """Повертає текстовий опис складових замовлення."""
        return " + ".join(f"{name}: {cost} грн" for name, cost in self.get_receipt_lines())


class BaseRoomStay(PricedItem):
    """
    Конкретний компонент (Concrete Component).
    Базове проживання в номері на визначену кількість діб без додаткових послуг.
    """

    def __init__(self, room: Room, nights: int):
        if nights <= 0:
            raise ValueError("Кількість діб має бути більшою за 0.")
        self.room = room
        self._nights = nights

    @property
    def nights(self) -> int:
        return self._nights

    def calculate_cost(self) -> float:
        """Вартість номера за вказану кількість діб."""
        return round(self.room.base_price_per_night * self._nights, 2)

    def get_receipt_lines(self) -> List[ReceiptLine]:
        return [(
            f"Проживання в номері {self.room.room_number} ({self.room.room_type.value}), "
            f"{self._nights} ноч. × {self.room.base_price_per_night}",
            self.calculate_cost(),
        )]


class ServiceDecorator(PricedItem, ABC):
    """
    Базовий декоратор (Base Decorator).
    Обгортає PricedItem і додає до нього вартість однієї послуги.
    """

    def __init__(self, wrappee: PricedItem, service: AdditionalService):
        self._wrappee = wrappee
        self.service = service

    @property
    def wrappee(self) -> PricedItem:
        return self._wrappee

    @property
    def nights(self) -> int:
        return self._wrappee.nights

    @abstractmethod
    def service_cost(self) -> float:
        """Вартість саме цієї послуги."""

    def calculate_cost(self) -> float:
        return round(self._wrappee.calculate_cost() + self.service_cost(), 2)

    def get_receipt_lines(self) -> List[ReceiptLine]:
        return self._wrappee.get_receipt_lines() + [(self._line_title(), self.service_cost())]

    def _line_title(self) -> str:
        return self.service.name


class PerNightServiceDecorator(ServiceDecorator):
    """Конкретний декоратор: послуга, що тарифікується за кожну ніч (напр. сніданок)."""

    def service_cost(self) -> float:
        return round(self.service.price * self.nights, 2)

    def _line_title(self) -> str:
        return f"{self.service.name}, {self.nights} ноч. × {self.service.price}"


class OneTimeServiceDecorator(ServiceDecorator):
    """Конкретний декоратор: разова послуга (трансфер, SPA, прибирання, екскурсія)."""

    def service_cost(self) -> float:
        return round(self.service.price, 2)


def decorate_with_service(item: PricedItem, service: AdditionalService) -> PricedItem:
    """Обирає відповідний декоратор за типом послуги."""
    if service.service_type in PER_NIGHT_SERVICE_TYPES:
        return PerNightServiceDecorator(item, service)
    return OneTimeServiceDecorator(item, service)


def build_priced_stay(room: Room, nights: int, services: Iterable[AdditionalService]) -> PricedItem:
    """Будує ланцюжок: проживання, обгорнуте декораторами всіх обраних послуг."""
    item: PricedItem = BaseRoomStay(room, nights)
    for service in services:
        item = decorate_with_service(item, service)
    return item
