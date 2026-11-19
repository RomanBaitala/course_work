"""
Сервіс бронювання — прикладний шар між REST-контролерами та доменом.

Контролери лише перетворюють HTTP-запити у виклики цього сервісу. Усі бізнес-правила
бронювання зібрані в одному місці:

    • перевірка гостя, номера, послуг, дат і доступності номера;
    • розрахунок вартості: Decorator (послуги) + Strategy (тариф обирає сервер);
    • збирання бронювання через Builder;
    • зміна статусів лише через State (BookingLifecycle);
    • публікація подій для слухачів Observer (сповіщення, бонуси, статус номера).

[GoF Pattern: Facade / Структурний патерн]
BookingService надає контролерам простий інтерфейс до підсистеми з кількох
компонентів (репозиторії, ціноутворення, Builder, State, події), тому контролери
не залежать від їхніх деталей (Low Coupling, GRASP Controller).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Optional, Tuple

from app.domain.booking import BookingLifecycle, InvalidStateTransitionError
from app.domain.builders.booking_builder import BookingBuildError, BookingBuilder
from app.domain.events import (
    BookingEvent,
    BookingEventManager,
    BookingEventType,
    LoyaltyBonusListener,
    NotificationListener,
    RoomStatusListener,
)
from app.domain.models.entities import AdditionalService, Booking, Room, User
from app.domain.pricing.pricing_strategy import PricingCalculatorContext, select_pricing_strategy
from app.domain.pricing.service_decorator import build_priced_stay


# ------------------------------------------------------------------ помилки ---

class BookingError(Exception):
    """Помилка бізнес-правил бронювання. http_status підказує контролеру код відповіді."""

    http_status = 400


class NotFoundError(BookingError):
    http_status = 404


class ForbiddenError(BookingError):
    http_status = 403


class RoomUnavailableError(BookingError):
    http_status = 409


class InvalidTransitionError(BookingError):
    http_status = 409


# --------------------------------------------------------- розрахунок ціни ---

@dataclass
class PriceQuote:
    """Детальний розрахунок вартості бронювання (основа для чека та калькулятора в UI)."""

    nights: int
    subtotal: float                      # проживання + послуги
    tariff: str                          # опис застосованої стратегії
    price_after_tariff: float
    bonus_used: float
    total: float                         # до сплати
    bonus_to_earn: float                 # нарахується після виселення
    receipt_lines: List[Tuple[str, float]] = field(default_factory=list)


# ------------------------------------------------------------------- сервіс ---

class BookingService:
    """Усі сценарії роботи з бронюванням: створення, розрахунок, зміна статусів."""

    # дія State-машини → подія для слухачів
    ACTION_EVENTS = {
        "confirm": BookingEventType.CONFIRMED,
        "check_in": BookingEventType.CHECKED_IN,
        "check_out": BookingEventType.CHECKED_OUT,
        "cancel": BookingEventType.CANCELLED,
    }

    def __init__(self, user_repo, room_repo, service_repo, booking_repo, events: BookingEventManager):
        self.users = user_repo
        self.rooms = room_repo
        self.services = service_repo
        self.bookings = booking_repo
        self.events = events

    # --------------------------------------------------------- завантаження ---

    def _get_guest(self, guest_id: str) -> User:
        guest = self.users.get_by_id(guest_id)
        if not guest:
            raise NotFoundError(f"Користувача з ID '{guest_id}' не знайдено.")
        return guest

    def _get_room(self, room_id: str) -> Room:
        room = self.rooms.get_by_id(room_id)
        if not room:
            raise NotFoundError(f"Номер з ID '{room_id}' не знайдено.")
        return room

    def _get_services(self, service_ids: Iterable[str]) -> List[AdditionalService]:
        result = []
        for service_id in service_ids:
            service = self.services.get_by_id(service_id)
            if not service:
                raise NotFoundError(f"Послугу з ID '{service_id}' не знайдено.")
            result.append(service)
        return result

    def get_booking(self, booking_id: str) -> Booking:
        booking = self.bookings.get_by_id(booking_id)
        if not booking:
            raise NotFoundError(f"Бронювання '{booking_id}' не знайдено.")
        return booking

    # ----------------------------------------------------------- розрахунок ---

    def calculate_price(
        self,
        guest: User,
        room: Room,
        check_in: date,
        check_out: date,
        services: Iterable[AdditionalService] = (),
        bonus_to_use: float = 0.0,
    ) -> PriceQuote:
        """Розраховує вартість: послуги (Decorator) → тариф (Strategy) → списання бонусів."""
        if check_out <= check_in:
            raise BookingError("Дата виїзду повинна бути пізнішою за дату заїзду.")
        nights = (check_out - check_in).days

        stay = build_priced_stay(room, nights, list(services))
        subtotal = stay.calculate_cost()

        strategy = select_pricing_strategy(subtotal, check_in, check_out, guest)
        price_after_tariff = PricingCalculatorContext(strategy).calculate(subtotal, nights, guest)

        # Бонусами не можна оплатити більше, ніж є на рахунку, і більше за саму вартість
        bonus_used = round(min(max(bonus_to_use, 0.0), guest.bonus_points, price_after_tariff), 2)
        total = round(price_after_tariff - bonus_used, 2)

        return PriceQuote(
            nights=nights,
            subtotal=subtotal,
            tariff=strategy.get_description(),
            price_after_tariff=price_after_tariff,
            bonus_used=bonus_used,
            total=total,
            bonus_to_earn=round(total * guest.get_cashback_rate(), 2),
            receipt_lines=stay.get_receipt_lines(),
        )

    # ------------------------------------------------------------ створення ---

    def create_booking(
        self,
        guest_id: str,
        room_id: str,
        check_in: date,
        check_out: date,
        service_ids: Iterable[str] = (),
        bonus_to_use: float = 0.0,
        today: Optional[date] = None,
    ) -> Booking:
        guest = self._get_guest(guest_id)
        room = self._get_room(room_id)
        services = self._get_services(service_ids)

        if check_in < (today or date.today()):
            raise BookingError("Дата заїзду не може бути в минулому.")
        if not self.bookings.is_room_available(room.id, check_in, check_out):
            raise RoomUnavailableError(
                f"Номер {room.room_number} вже зайнятий на вибрані дати ({check_in} - {check_out})."
            )

        quote = self.calculate_price(guest, room, check_in, check_out, services, bonus_to_use)

        try:
            booking = (
                BookingBuilder()
                .set_guest(guest)
                .set_room(room)
                .set_dates(check_in, check_out)
                .add_services(services)
                .apply_bonus_points(quote.bonus_used)
                .set_pricing(quote.total, quote.bonus_to_earn)
                .build()
            )
        except BookingBuildError as e:
            raise BookingError(str(e)) from e

        self.bookings.create(booking)

        # Списуємо лише використані бонуси. Кешбек нарахує LoyaltyBonusListener після виселення.
        if quote.bonus_used:
            guest.deduct_bonus_points(quote.bonus_used)
            self.users.update_bonus_points(guest.id, guest.bonus_points)

        self._publish(BookingEventType.CREATED, booking)
        return booking

    # -------------------------------------------------------- зміна статусу ---

    def change_status(self, booking_id: str, action: str) -> Booking:
        """Виконує дію (confirm / check_in / check_out / cancel) через State-машину."""
        if action not in self.ACTION_EVENTS:
            raise BookingError(f"Невідома дія '{action}'. Дозволені: {list(self.ACTION_EVENTS)}.")

        booking = self.get_booking(booking_id)
        lifecycle = BookingLifecycle(booking)
        try:
            lifecycle.apply_action(action)
        except InvalidStateTransitionError as e:
            raise InvalidTransitionError(str(e)) from e
        except ValueError as e:
            raise BookingError(str(e)) from e

        self.bookings.update_status(booking.id, booking.status)
        self._publish(self.ACTION_EVENTS[action], booking)
        return booking

    def cancel_booking(self, booking_id: str, guest_id: Optional[str] = None) -> Booking:
        """Скасування. Якщо передано guest_id — скасувати можна лише власне бронювання."""
        booking = self.get_booking(booking_id)
        if guest_id and booking.guest.id != guest_id:
            raise ForbiddenError("Неможливо скасувати чуже бронювання.")
        return self.change_status(booking_id, "cancel")

    @staticmethod
    def allowed_actions(booking: Booking) -> List[str]:
        """Дії, які дозволяє поточний стан бронювання (для кнопок в інтерфейсі)."""
        return BookingLifecycle(booking).allowed_actions()

    # ---------------------------------------------------------------- події ---

    def _publish(self, event_type: BookingEventType, booking: Booking) -> None:
        self.events.notify(BookingEvent(event_type, booking))


# ------------------------------------------------------------ збирання сервісу ---

def create_booking_service(manager=None) -> BookingService:
    """
    Створює сервіс з репозиторіями та підписує слухачів подій.
    manager — менеджер БД (за замовчуванням глобальний db_manager).
    """
    from app.database.connection import db_manager
    from app.repositories import BookingRepository, RoomRepository, ServiceRepository, UserRepository

    manager = manager or db_manager
    users, rooms, services = UserRepository(manager), RoomRepository(manager), ServiceRepository(manager)
    bookings = BookingRepository(manager, users, rooms, services)

    events = BookingEventManager()
    service = BookingService(users, rooms, services, bookings, events)

    service.notifier = NotificationListener()
    events.subscribe(service.notifier)  # усі події
    loyalty = LoyaltyBonusListener(users, bookings)
    events.subscribe(loyalty, BookingEventType.CHECKED_OUT)
    events.subscribe(loyalty, BookingEventType.CANCELLED)
    room_status = RoomStatusListener(rooms)
    events.subscribe(room_status, BookingEventType.CHECKED_IN)
    events.subscribe(room_status, BookingEventType.CHECKED_OUT)
    return service


_service: Optional[BookingService] = None


def get_booking_service() -> BookingService:
    """Спільний екземпляр сервісу для всіх контролерів (один набір слухачів і сповіщень)."""
    global _service
    if _service is None:
        _service = create_booking_service()
    return _service
