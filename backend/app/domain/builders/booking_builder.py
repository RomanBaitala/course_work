"""
Конструктор бронювань (BookingBuilder).

[GoF Pattern: Builder / Породжувальний патерн]
Інкапсулює покроковий процес створення складного об'єкта Booking (бронювання),
забезпечуючи централізовану валідацію дат, доступності номерів, прив'язки гостя та списку додаткових послуг.
Також включає BookingDirector для побудови типових комплексних пакетів проживання.
"""

from datetime import date, datetime
from typing import Iterable, List, Optional
import uuid

from app.domain.models.entities import AdditionalService, Booking, Room, User
from app.domain.models.enums import BookingStatus, RoomStatus


class BookingBuildError(ValueError):
    """Помилка валідації параметрів під час побудови об'єкта Booking."""
    pass


class BookingBuilder:
    """
    Будівельник (Builder) для покрокового конструювання об'єкта Booking.
    Надає текучий (Fluent) інтерфейс для зручного виклику методів ланцюжком.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> "BookingBuilder":
        """Скидає внутрішній стан будівельника до початкового."""
        self._id: Optional[str] = None
        self._guest: Optional[User] = None
        self._room: Optional[Room] = None
        self._check_in_date: Optional[date] = None
        self._check_out_date: Optional[date] = None
        self._services: List[AdditionalService] = []
        self._status: BookingStatus = BookingStatus.CREATED
        self._used_bonus_points: float = 0.0
        return self

    def set_id(self, booking_id: str) -> "BookingBuilder":
        """Встановлює унікальний ідентифікатор бронювання (якщо не задано — генерується автоматично)."""
        self._id = booking_id
        return self

    def set_guest(self, guest: User) -> "BookingBuilder":
        """Прив'язує клієнта (гостя), який здійснює бронювання."""
        if not guest:
            raise BookingBuildError("Гість (User) є обов'язковим для створення бронювання.")
        self._guest = guest
        return self

    def set_room(self, room: Room) -> "BookingBuilder":
        """Призначає готельний номер для бронювання з перевіркою його готовності."""
        if not room:
            raise BookingBuildError("Номер (Room) є обов'язковим для створення бронювання.")
        if room.status == RoomStatus.MAINTENANCE:
            raise BookingBuildError(f"Номер {room.room_number} знаходиться на технічному обслуговуванні.")
        self._room = room
        return self

    def set_dates(self, check_in: date, check_out: date) -> "BookingBuilder":
        """Встановлює період проживання та валідує хронологічну послідовність дат."""
        if not check_in or not check_out:
            raise BookingBuildError("Дати заїзду та виїзду мають бути вказані.")
        if check_out <= check_in:
            raise BookingBuildError(
                f"Дата виїзду ({check_out}) повинна бути пізнішою за дату заїзду ({check_in})."
            )
        self._check_in_date = check_in
        self._check_out_date = check_out
        return self

    def add_service(self, service: AdditionalService) -> "BookingBuilder":
        """Додає одну додаткову платну послугу (харчування, SPA, трансфер тощо)."""
        if service:
            self._services.append(service)
        return self

    def add_services(self, services: Iterable[AdditionalService]) -> "BookingBuilder":
        """Додає перелік додаткових послуг."""
        for s in services:
            self.add_service(s)
        return self

    def set_status(self, status: BookingStatus) -> "BookingBuilder":
        """Встановлює початковий статус бронювання."""
        self._status = status
        return self

    def apply_bonus_points(self, points: float) -> "BookingBuilder":
        """Фіксує кількість бонусних балів, які гість планує використати для знижки."""
        if points < 0:
            raise BookingBuildError("Кількість бонусних балів не може бути від'ємною.")
        if self._guest and points > self._guest.bonus_points:
            raise BookingBuildError(
                f"У гостя недостатньо бонусів: запитано {points}, наявно {self._guest.bonus_points}"
            )
        self._used_bonus_points = round(points, 2)
        return self

    def _validate(self) -> None:
        """Перевіряє повноту та цілісність усіх параметрів перед створенням об'єкта."""
        if self._guest is None:
            raise BookingBuildError("Неможливо створити бронювання без зазначення гостя (guest).")
        if self._room is None:
            raise BookingBuildError("Неможливо створити бронювання без вибору номера (room).")
        if self._check_in_date is None or self._check_out_date is None:
            raise BookingBuildError("Неможливо створити бронювання без вибору періоду проживання.")

    def build(self) -> Booking:
        """
        Завершальний етап побудови: валідує дані, розраховує початкову вартість
        і повертає сконструйований об'єкт Booking.
        """
        self._validate()

        nights = (self._check_out_date - self._check_in_date).days
        room_cost = self._room.base_price_per_night * nights
        services_cost = sum(service.price for service in self._services)
        initial_total = max(0.0, room_cost + services_cost - self._used_bonus_points)

        booking = Booking(
            id=self._id or str(uuid.uuid4()),
            guest=self._guest,
            room=self._room,
            check_in_date=self._check_in_date,
            check_out_date=self._check_out_date,
            services=list(self._services),
            status=self._status,
            total_price=round(initial_total, 2),
            used_bonus_points=self._used_bonus_points,
            created_at=datetime.now(),
        )

        return booking


class BookingDirector:
    """
    Директор (Director) у класичній схемі патерну Builder GoF.
    Оркеструє кроки конструювання для створення типових готових пакетів бронювання.
    """

    @staticmethod
    def construct_basic_stay(
        builder: BookingBuilder,
        guest: User,
        room: Room,
        check_in: date,
        check_out: date,
    ) -> Booking:
        """Створює базове стандартне бронювання номера без додаткових сервісів."""
        return (
            builder.reset()
            .set_guest(guest)
            .set_room(room)
            .set_dates(check_in, check_out)
            .build()
        )

    @staticmethod
    def construct_vip_package(
        builder: BookingBuilder,
        guest: User,
        room: Room,
        check_in: date,
        check_out: date,
        spa_service: AdditionalService,
        transfer_service: AdditionalService,
        meal_service: AdditionalService,
    ) -> Booking:
        """Створює комплексне VIP-бронювання з повним набором послуг."""
        return (
            builder.reset()
            .set_guest(guest)
            .set_room(room)
            .set_dates(check_in, check_out)
            .add_service(meal_service)
            .add_service(transfer_service)
            .add_service(spa_service)
            .build()
        )
