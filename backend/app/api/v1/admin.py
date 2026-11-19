"""
Endpoints for Hotel Administration and Analytics Reports.
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.bookings import _booking_to_response, http_error
from app.api.v1.schemas import (
    BookingResponse,
    FinancialReportResponse,
    OccupancyReportResponse,
    UpdateBookingStatusRequest,
)
from app.domain.models.enums import BookingStatus, RoomStatus
from app.repositories import BookingRepository, RoomRepository
from app.services.booking_service import BookingError, get_booking_service

router = APIRouter(prefix="/admin", tags=["Admin & Analytics"])
booking_repo = BookingRepository()
room_repo = RoomRepository()


@router.get("/reports/financial", response_model=FinancialReportResponse, summary="Фінансовий звіт для керівництва")
def get_financial_report():
    """Повертає загальну виручку, помісячну динаміку та прибутковість за категоріями номерів."""
    summary = booking_repo.get_financial_summary()
    return FinancialReportResponse(
        total_bookings=summary["total_bookings"],
        total_revenue=summary["total_revenue"],
        avg_booking_value=summary["avg_booking_value"],
        monthly_revenue=summary["monthly_revenue"],
        revenue_by_category=summary["revenue_by_category"],
    )


@router.get("/reports/occupancy", response_model=OccupancyReportResponse, summary="Звіт про завантаженість номерного фонду")
def get_occupancy_report():
    """Розраховує поточний відсоток завантаженості номерів."""
    all_rooms = room_repo.get_all()
    total = len(all_rooms)
    available = len([r for r in all_rooms if r.status == RoomStatus.AVAILABLE])
    occupied = total - available

    rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

    return OccupancyReportResponse(
        total_rooms=total,
        available_rooms=available,
        occupied_rooms=occupied,
        occupancy_rate_percentage=rate,
    )


@router.get("/bookings", response_model=List[BookingResponse], summary="Перегляд усіх бронювань готелю")
def get_all_hotel_bookings(
    status: Optional[BookingStatus] = None,
):
    bookings = booking_repo.get_all(status=status)
    return [_booking_to_response(b) for b in bookings]


# Цільовий статус → дія State-машини (повернути бронювання в «created» неможливо)
STATUS_TO_ACTION = {
    BookingStatus.CONFIRMED: "confirm",
    BookingStatus.CHECKED_IN: "check_in",
    BookingStatus.CHECKED_OUT: "check_out",
    BookingStatus.CANCELLED: "cancel",
}


@router.patch("/bookings/{booking_id}/status", summary="Змінити статус бронювання")
def update_booking_status(booking_id: str, req: UpdateBookingStatusRequest):
    """
    Змінює статус через State-машину: недопустимі переходи (напр. заселити скасоване
    бронювання) повертають 409. Статус номера та бонуси оновлюють слухачі подій.
    """
    try:
        new_status = BookingStatus(req.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Некоректний статус. Дозволені: {[s.value for s in BookingStatus]}",
        )
    action = STATUS_TO_ACTION.get(new_status)
    if not action:
        raise HTTPException(status_code=400, detail="Повернути бронювання у статус 'created' неможливо.")

    try:
        booking = get_booking_service().change_status(booking_id, action)
    except BookingError as e:
        raise http_error(e)

    return {
        "message": f"Статус бронювання '{booking_id}' оновлено на '{booking.status.value}'.",
        "booking_id": booking_id,
        "status": booking.status.value,
    }
