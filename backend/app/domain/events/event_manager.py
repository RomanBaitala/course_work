"""
Система доменних подій бронювання.

[GoF Pattern: Observer / Поведінковий патерн]
BookingEventManager (Subject / Publisher) зберігає список підписників для кожного
типу події та сповіщає їх, коли з бронюванням щось відбувається.
Фасад бронювання лише публікує подію і нічого не знає про те, хто і як на неї
реагує: надсилання листів, нарахування бонусів, оновлення статусу номера.
Нові реакції додаються підпискою нового слухача, без зміни коду фасаду (OCP, Low Coupling).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.models.entities import Booking


class BookingEventType(str, Enum):
    """Типи подій життєвого циклу бронювання."""

    CREATED = "booking_created"
    CONFIRMED = "booking_confirmed"
    CHECKED_IN = "booking_checked_in"
    CHECKED_OUT = "booking_checked_out"
    CANCELLED = "booking_cancelled"
    EXTENDED = "booking_extended"


@dataclass
class BookingEvent:
    """Об'єкт події, що передається підписникам."""

    event_type: BookingEventType
    booking: Booking
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=datetime.now)


class BookingEventListener(ABC):
    """Інтерфейс спостерігача (Observer)."""

    @abstractmethod
    def update(self, event: BookingEvent) -> None:
        """Реакція на подію."""


class BookingEventManager:
    """
    Суб'єкт (Subject) патерну Observer.
    Підтримує підписку як на конкретний тип події, так і на всі події одразу (event_type=None).
    """

    def __init__(self) -> None:
        self._listeners: Dict[Optional[BookingEventType], List[BookingEventListener]] = {}

    def subscribe(
        self, listener: BookingEventListener, event_type: Optional[BookingEventType] = None
    ) -> None:
        bucket = self._listeners.setdefault(event_type, [])
        if listener not in bucket:
            bucket.append(listener)

    def unsubscribe(
        self, listener: BookingEventListener, event_type: Optional[BookingEventType] = None
    ) -> None:
        bucket = self._listeners.get(event_type, [])
        if listener in bucket:
            bucket.remove(listener)

    def listeners_for(self, event_type: BookingEventType) -> List[BookingEventListener]:
        return self._listeners.get(event_type, []) + self._listeners.get(None, [])

    def notify(self, event: BookingEvent) -> None:
        """Розсилає подію всім зацікавленим підписникам."""
        for listener in self.listeners_for(event.event_type):
            listener.update(event)
