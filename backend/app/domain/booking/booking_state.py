"""
Життєвий цикл бронювання.

[GoF Pattern: State / Поведінковий патерн]
Кожен статус бронювання представлений окремим класом-станом, який сам вирішує,
які дії дозволені, і в який стан перейти. Контекст (BookingLifecycle) делегує
виклики поточному стану, тому в коді немає громіздких if/elif по статусах,
а додавання нового статусу не вимагає змін в існуючих класах (OCP).

Граф переходів:

    Created ──confirm──► Confirmed ──check_in──► CheckedIn ──check_out──► CheckedOut
       │                    │                        │
       └──────cancel────────┴──────► Cancelled       └── extend (продовження)
    (extend дозволений у станах Created / Confirmed / CheckedIn)
"""

from __future__ import annotations

from abc import ABC
from datetime import date
from typing import Dict, List, Optional, Type

from app.domain.models.entities import Booking
from app.domain.models.enums import BookingStatus

class InvalidStateTransitionError(Exception):
    """Спроба виконати дію, недопустиму для поточного стану бронювання."""

    def __init__(self, state: "BookingState", action: str):
        self.status = state.status
        self.action = action
        super().__init__(
            f"Дія «{action}» недоступна для бронювання у статусі «{state.title}»."
        )


class BookingState(ABC):
    """
    Абстрактний стан (State).
    За замовчуванням усі дії заборонені — конкретні стани перевизначають лише дозволені.
    """

    status: BookingStatus
    title: str

    def __init__(self, lifecycle: "BookingLifecycle"):
        self.lifecycle = lifecycle

    # --- дії, що змінюють стан ---
    def confirm(self) -> None:
        raise InvalidStateTransitionError(self, "підтвердити")

    def check_in(self, today: Optional[date] = None) -> None:
        raise InvalidStateTransitionError(self, "заселити")

    def check_out(self) -> None:
        raise InvalidStateTransitionError(self, "виселити")

    def cancel(self) -> None:
        raise InvalidStateTransitionError(self, "скасувати")

    def extend(self, new_check_out: date) -> None:
        raise InvalidStateTransitionError(self, "продовжити")

    # --- допоміжне ---
    def allowed_actions(self) -> List[str]:
        """Перелік дій, доступних у цьому стані (для кнопок у UI)."""
        return []

    def _extend_dates(self, new_check_out: date) -> None:
        booking = self.lifecycle.booking
        if new_check_out <= booking.check_out_date:
            raise ValueError("Нова дата виїзду має бути пізнішою за поточну.")
        booking.check_out_date = new_check_out

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class CreatedState(BookingState):
    """Бронювання створене клієнтом і очікує підтвердження адміністратором."""

    status = BookingStatus.CREATED
    title = "Створено"

    def confirm(self) -> None:
        self.lifecycle.transition_to(ConfirmedState)

    def cancel(self) -> None:
        self.lifecycle.transition_to(CancelledState)

    def extend(self, new_check_out: date) -> None:
        self._extend_dates(new_check_out)

    def allowed_actions(self) -> List[str]:
        return ["confirm", "cancel", "extend"]


class ConfirmedState(BookingState):
    """Бронювання підтверджене готелем, номер закріплено за гостем."""

    status = BookingStatus.CONFIRMED
    title = "Підтверджено"

    def check_in(self, today: Optional[date] = None) -> None:
        today = today or date.today()
        booking = self.lifecycle.booking
        if today > booking.check_out_date:
            raise ValueError("Неможливо заселити: період бронювання вже минув.")
        self.lifecycle.transition_to(CheckedInState)

    def cancel(self) -> None:
        self.lifecycle.transition_to(CancelledState)

    def extend(self, new_check_out: date) -> None:
        self._extend_dates(new_check_out)

    def allowed_actions(self) -> List[str]:
        return ["check_in", "cancel", "extend"]


class CheckedInState(BookingState):
    """Гість проживає в номері. Скасування вже неможливе, лише виселення або продовження."""

    status = BookingStatus.CHECKED_IN
    title = "Заселено"

    def check_out(self) -> None:
        self.lifecycle.transition_to(CheckedOutState)

    def extend(self, new_check_out: date) -> None:
        self._extend_dates(new_check_out)

    def allowed_actions(self) -> List[str]:
        return ["check_out", "extend"]


class CheckedOutState(BookingState):
    """Фінальний стан: проживання завершено успішно."""

    status = BookingStatus.CHECKED_OUT
    title = "Виселено"


class CancelledState(BookingState):
    """Фінальний стан: бронювання скасоване."""

    status = BookingStatus.CANCELLED
    title = "Скасовано"


# Реєстр відповідності статусу (з БД) до класу стану
STATE_REGISTRY: Dict[BookingStatus, Type[BookingState]] = {
    cls.status: cls
    for cls in (CreatedState, ConfirmedState, CheckedInState, CheckedOutState, CancelledState)
}


class BookingLifecycle:
    """
    Контекст (Context) патерну State.
    Обгортає сутність Booking, зберігає поточний стан і синхронізує booking.status.
    """

    def __init__(self, booking: Booking):
        self.booking = booking
        self._state: BookingState = STATE_REGISTRY[booking.status](self)
        self.history: List[BookingStatus] = [booking.status]

    @property
    def state(self) -> BookingState:
        return self._state

    @property
    def status(self) -> BookingStatus:
        return self._state.status

    def transition_to(self, state_cls: Type[BookingState]) -> None:
        """Виконує перехід у новий стан (викликається лише самими станами)."""
        self._state = state_cls(self)
        self.booking.status = self._state.status
        self.history.append(self._state.status)

    # Делегування дій поточному стану
    def confirm(self) -> None:
        self._state.confirm()

    def check_in(self, today: Optional[date] = None) -> None:
        self._state.check_in(today)

    def check_out(self) -> None:
        self._state.check_out()

    def cancel(self) -> None:
        self._state.cancel()

    def extend(self, new_check_out: date) -> None:
        self._state.extend(new_check_out)

    def allowed_actions(self) -> List[str]:
        return self._state.allowed_actions()

    def apply_action(self, action: str, **kwargs) -> None:
        """Виконує дію за назвою (використовується REST API адміністратора)."""
        handlers = {
            "confirm": self.confirm,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "cancel": self.cancel,
            "extend": self.extend,
        }
        if action not in handlers:
            raise ValueError(f"Невідома дія: {action}")
        handlers[action](**kwargs)
