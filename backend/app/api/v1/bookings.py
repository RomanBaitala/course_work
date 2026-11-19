"""
Endpoints for Hotel Bookings creation, history, and status updates.

Контролер «тонкий»: уся логіка бронювання — у BookingService (app/services/booking_service.py).
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException, status

from app.api.v1.rooms import _entity_to_response as _room_to_response
from app.api.v1.schemas import (
    BookingResponse,
    CreateBookingRequest,
    ServiceResponse,
)
from app.api.v1.users import _user_to_response
from app.services.booking_service import BookingError, get_booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def http_error(e: BookingError) -> HTTPException:
    """Перетворює помилку бізнес-правил на HTTP-відповідь з відповідним кодом."""
    return HTTPException(status_code=e.http_status, detail=str(e))


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
    Створює бронювання: перевірка доступності номера, розрахунок вартості
    (послуги + тариф, який обирає сервер), списання бонусів, сповіщення гостю.
    Кешбек нараховується лише після виселення.
    """
    try:
        booking = get_booking_service().create_booking(
            req.guest_id,
            req.room_id,
            req.check_in_date,
            req.check_out_date,
            req.service_ids,
            req.use_bonus_points,
        )
    except BookingError as e:
        raise http_error(e)
    return _booking_to_response(booking)


@router.get("/{booking_id}", response_model=BookingResponse, summary="Деталі бронювання за ID")
def get_booking(booking_id: str):
    try:
        return _booking_to_response(get_booking_service().get_booking(booking_id))
    except BookingError as e:
        raise http_error(e)


@router.get("/my/{guest_id}", response_model=List[BookingResponse], summary="Особистий кабінет: історія бронювань клієнта")
def get_my_bookings(guest_id: str):
    bookings = get_booking_service().bookings.get_by_guest_id(guest_id)
    return [_booking_to_response(b) for b in bookings]


@router.patch("/{booking_id}/cancel", summary="Скасувати бронювання")
def cancel_booking(booking_id: str, guest_id: Optional[str] = None):
    """Скасування з поверненням списаних бонусів. З guest_id перевіряється, що бронювання належить гостю."""
    try:
        booking = get_booking_service().cancel_booking(booking_id, guest_id)
    except BookingError as e:
        raise http_error(e)
    return {
        "message": f"Бронювання '{booking_id}' успішно скасовано.",
        "status": booking.status.value,
        "refunded_bonus_points": booking.used_bonus_points,
    }
