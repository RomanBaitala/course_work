"""
Endpoints for Hotel Bookings creation, history, and status updates.
"""

from datetime import date
import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException, status

from app.api.v1.rooms import _entity_to_response as _room_to_response
from app.api.v1.schemas import (
    BookingResponse,
    CreateBookingRequest,
    ServiceResponse,
    UserResponse,
)
from app.api.v1.users import _user_to_response
from app.domain.builders.booking_builder import BookingBuildError, BookingBuilder
from app.domain.models.enums import BookingStatus
from app.domain.pricing.pricing_strategy import (
    LongStayDiscountStrategy,
    LoyaltyPricingStrategy,
    PricingCalculatorContext,
    StandardPricingStrategy,
    WeekendSurchargeStrategy,
)
from app.domain.pricing.service_decorator import (
    build_priced_stay,
)
from app.repositories import (
    BookingRepository,
    RoomRepository,
    ServiceRepository,
    UserRepository,
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])
booking_repo = BookingRepository()
room_repo = RoomRepository()
user_repo = UserRepository()
service_repo = ServiceRepository()


def _booking_to_response(b) -> BookingResponse:
    return BookingResponse(
        id=b.id,
        guest=_user_to_response(b.guest),
        room=_room_to_response(b.room),
        check_in_date=b.check_in_date,
        check_out_date=b.check_out_date,
        nights_count=b.nights_count,
        services=[
            ServiceResponse(
                id=s.id,
                name=s.name,
                service_type=s.service_type.value,
                price=s.price,
                description=s.description,
            )
            for s in b.services
        ],
        status=b.status.value,
        total_price=b.total_price,
        used_bonus_points=b.used_bonus_points,
        earned_bonus_points=b.earned_bonus_points,
        created_at=b.created_at,
    )


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, summary="Створити нове бронювання")
def create_booking(req: CreateBookingRequest):
    """
    Створює бронювання з перевіркою доступності номера,
    декоруванням обраних додаткових послуг та розрахунком тарифу.
    """
    # 1. Перевірка наявності гостя та кімнати
    guest = user_repo.get_by_id(req.guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail=f"Користувача з ID '{req.guest_id}' не знайдено.")

    room = room_repo.get_by_id(req.room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Номер з ID '{req.room_id}' не знайдено.")

    # 2. Перевірка дат
    if req.check_out_date <= req.check_in_date:
        raise HTTPException(status_code=400, detail="Дата виїзду повинна бути пізнішою за дату заїзду.")

    # 3. Перевірка зайнятості номера
    if not booking_repo.is_room_available(room.id, req.check_in_date, req.check_out_date):
        raise HTTPException(
            status_code=409,
            detail=f"Номер {room.room_number} вже зайнятий на вибрані дати ({req.check_in_date} - {req.check_out_date}).",
        )

    # 4. Отримання обраних сервісів
    selected_services = []
    for s_id in req.service_ids:
        srv = service_repo.get_by_id(s_id)
        if srv:
            selected_services.append(srv)

    # 5. Розрахунок вартості через Decorator & Strategy
    nights = (req.check_out_date - req.check_in_date).days
    priced_item = build_priced_stay(room, nights, selected_services)

    subtotal = priced_item.calculate_cost()

    # Вибір стратегії ціноутворення
    strategies = {
        "standard": StandardPricingStrategy(),
        "long_stay": LongStayDiscountStrategy(),
        "loyalty": LoyaltyPricingStrategy(),
        "weekend": WeekendSurchargeStrategy(),
    }
    strategy = strategies.get(req.pricing_strategy, StandardPricingStrategy())
    context = PricingCalculatorContext(strategy)
    calculated_price = context.calculate(subtotal, nights=nights, guest=guest)

    # Списання бонусів
    used_bonuses = min(guest.bonus_points, req.use_bonus_points)
    final_total = max(0.0, round(calculated_price - used_bonuses, 2))

    # Нарахування кешбеку в бонусах за проживання
    earned_bonuses = round(final_total * guest.get_cashback_rate(), 2)

    # 6. Побудова об'єкта бронювання через Builder
    builder = BookingBuilder()
    try:
        booking = (
            builder.reset()
            .set_guest(guest)
            .set_room(room)
            .set_dates(req.check_in_date, req.check_out_date)
            .add_services(selected_services)
            .apply_bonus_points(used_bonuses)
            .set_pricing(final_total, earned_bonuses)
            .build()
        )
    except BookingBuildError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 7. Збереження в базу даних
    saved_booking = booking_repo.create(booking)

    # Оновлення балансу бонусів клієнта
    new_bonus_balance = round(guest.bonus_points - used_bonuses + earned_bonuses, 2)
    user_repo.update_bonus_points(guest.id, new_bonus_balance)
    saved_booking.guest.bonus_points = new_bonus_balance

    return _booking_to_response(saved_booking)


@router.get("/{booking_id}", response_model=BookingResponse, summary="Деталі бронювання за ID")
def get_booking(booking_id: str):
    booking = booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail=f"Бронювання '{booking_id}' не знайдено.")
    return _booking_to_response(booking)


@router.get("/my/{guest_id}", response_model=List[BookingResponse], summary="Особистий кабінет: історія бронювань клієнта")
def get_my_bookings(guest_id: str):
    bookings = booking_repo.get_by_guest_id(guest_id)
    return [_booking_to_response(b) for b in bookings]


@router.patch("/{booking_id}/cancel", summary="Скасувати бронювання")
def cancel_booking(booking_id: str):
    booking = booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail=f"Бронювання '{booking_id}' не знайдено.")
    if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
        raise HTTPException(status_code=400, detail="Неможливо скасувати замовлення, яке вже проживає або виселено.")

    booking_repo.update_status(booking_id, BookingStatus.CANCELLED)
    return {"message": f"Бронювання '{booking_id}' успішно скасовано.", "status": "cancelled"}
