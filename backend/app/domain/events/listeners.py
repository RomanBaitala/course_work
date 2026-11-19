"""
Конкретні спостерігачі (Concrete Observers) подій бронювання.

Залежності (репозиторії) передаються через конструктор, тому слухачі залежать
від абстракцій із потрібними методами, а не від конкретної БД (DIP).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Dict, List, Optional, Protocol

from app.domain.events.event_manager import (
    BookingEvent,
    BookingEventListener,
    BookingEventType,
)
from app.domain.models.enums import LoyaltyTier, RoomStatus


@dataclass
class Notification:
    """Повідомлення, надіслане гостю (імітація email / SMS)."""

    recipient: str
    channel: str
    subject: str
    message: str
    sent_at: datetime = field(default_factory=datetime.now)


class NotificationListener(BookingEventListener):
    """
    Надсилає гостю повідомлення про зміну статусу бронювання.
    У навчальному проєкті повідомлення не відправляються реально, а зберігаються в outbox та логуються.
    """

    TEMPLATES = {
        BookingEventType.CREATED: ("Бронювання прийнято", "Ваше бронювання №{id} на номер {room} ({check_in} – {check_out}) створено. Сума: {total} грн."),
        BookingEventType.CONFIRMED: ("Бронювання підтверджено", "Бронювання №{id} підтверджене. Чекаємо на вас {check_in}!"),
        BookingEventType.CHECKED_IN: ("Ласкаво просимо!", "Ви заселилися в номер {room}. Гарного відпочинку!"),
        BookingEventType.CHECKED_OUT: ("Дякуємо за візит", "Проживання завершено. Нараховано бонусів: {earned}."),
        BookingEventType.CANCELLED: ("Бронювання скасовано", "Бронювання №{id} скасовано. Використані бонуси повернено на рахунок."),
        BookingEventType.EXTENDED: ("Проживання продовжено", "Нова дата виїзду: {check_out}. Нова сума: {total} грн."),
    }

    def __init__(self) -> None:
        self.outbox: List[Notification] = []
        self._logger = logging.getLogger("hotel")

    def update(self, event: BookingEvent) -> None:
        b = event.booking
        subject, template = self.TEMPLATES[event.event_type]
        text = template.format(
            id=b.id[:8],
            room=b.room.room_number,
            check_in=b.check_in_date.isoformat(),
            check_out=b.check_out_date.isoformat(),
            total=b.total_price,
            earned=b.earned_bonus_points,
        )
        for channel, address in (("email", b.guest.email), ("sms", b.guest.phone)):
            if address:
                self.outbox.append(Notification(address, channel, subject, text))
        self._logger.info("Notification → %s: %s", b.guest.email, subject)


class UserStore(Protocol):
    def get_by_id(self, user_id: str): ...
    def save(self, user): ...


class BookingStore(Protocol):
    def count_completed_by_guest(self, guest_id: str) -> int: ...


class LoyaltyBonusListener(BookingEventListener):
    """
    Програма лояльності:
      • при виселенні нараховує кешбек (earned_bonus_points) та підвищує рівень картки;
      • при скасуванні повертає списані бонуси.
    """

    TIER_ORDER = [LoyaltyTier.STANDARD, LoyaltyTier.SILVER, LoyaltyTier.GOLD, LoyaltyTier.PLATINUM]
    # Кількість завершених проживань для переходу на рівень
    DEFAULT_THRESHOLDS = {"silver": 2, "gold": 5, "platinum": 10}

    def __init__(self, user_repo: UserStore, booking_repo: BookingStore,
                 thresholds: Optional[Dict[str, int]] = None) -> None:
        self.user_repo = user_repo
        self.booking_repo = booking_repo
        self.thresholds = thresholds or dict(self.DEFAULT_THRESHOLDS)

    def update(self, event: BookingEvent) -> None:
        if event.event_type == BookingEventType.CHECKED_OUT:
            self._credit_cashback(event)
        elif event.event_type == BookingEventType.CANCELLED:
            self._refund_used_bonuses(event)

    def _credit_cashback(self, event: BookingEvent) -> None:
        user = self.user_repo.get_by_id(event.booking.guest.id)
        if not user:
            return
        user.add_bonus_points(event.booking.earned_bonus_points)
        user.loyalty_tier = self._calc_tier(user.loyalty_tier, user.id)
        self.user_repo.save(user)
        event.booking.guest = user

    def _refund_used_bonuses(self, event: BookingEvent) -> None:
        if event.booking.used_bonus_points <= 0:
            return
        user = self.user_repo.get_by_id(event.booking.guest.id)
        if not user:
            return
        user.add_bonus_points(event.booking.used_bonus_points)
        self.user_repo.save(user)
        event.booking.guest = user

    def _calc_tier(self, current: LoyaltyTier, user_id: str) -> LoyaltyTier:
        """Рівень лише зростає: визначається кількістю завершених проживань."""
        stays = self.booking_repo.count_completed_by_guest(user_id)
        thresholds = self.thresholds
        earned = LoyaltyTier.STANDARD
        for tier in self.TIER_ORDER[1:]:
            if stays >= thresholds[tier.value]:
                earned = tier
        return max(current, earned, key=self.TIER_ORDER.index)


class RoomStore(Protocol):
    def update_status(self, room_id: str, status: RoomStatus) -> bool: ...


class RoomStatusListener(BookingEventListener):
    """Синхронізує експлуатаційний статус номера з подіями заселення / виселення."""

    def __init__(self, room_repo: RoomStore) -> None:
        self.room_repo = room_repo

    def update(self, event: BookingEvent) -> None:
        room_id = event.booking.room.id
        if event.event_type == BookingEventType.CHECKED_IN:
            self.room_repo.update_status(room_id, RoomStatus.OCCUPIED)
            event.booking.room.status = RoomStatus.OCCUPIED
        elif event.event_type == BookingEventType.CHECKED_OUT:
            self.room_repo.update_status(room_id, RoomStatus.AVAILABLE)
            event.booking.room.status = RoomStatus.AVAILABLE
