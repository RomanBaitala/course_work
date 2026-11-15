"""
Pydantic DTO (Data Transfer Objects) schemas for FastAPI endpoints.
Ensures strong typing, request validation, and automatic OpenAPI schema generation.
"""

from datetime import date, datetime
from typing import List, Optional
import os
import sys

# Ensure backend/libs is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))

from pydantic import BaseModel, Field


# --- Room Schemas ---

class RoomResponse(BaseModel):
    id: str
    room_number: str
    room_type: str
    base_price_per_night: float
    capacity: int
    description: str
    amenities: List[str]
    status: str
    photo_urls: List[str]


# --- Service Schemas ---

class ServiceResponse(BaseModel):
    id: str
    name: str
    service_type: str
    price: float
    description: str


# --- User Schemas ---

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    role: str
    loyalty_tier: str
    bonus_points: float
    created_at: datetime


# --- Booking Schemas ---

class CreateBookingRequest(BaseModel):
    guest_id: str = Field(..., description="ID користувача, який здійснює бронювання")
    room_id: str = Field(..., description="ID номера готелю")
    check_in_date: date = Field(..., description="Дата заїзду (YYYY-MM-DD)")
    check_out_date: date = Field(..., description="Дата виїзду (YYYY-MM-DD)")
    service_ids: List[str] = Field(default_factory=list, description="Список ID додаткових послуг")
    use_bonus_points: float = Field(0.0, ge=0.0, description="Кількість бонусних балів для списання")
    pricing_strategy: str = Field("standard", description="Стратегія розрахунку (standard, long_stay, loyalty, weekend)")


class BookingResponse(BaseModel):
    id: str
    guest: UserResponse
    room: RoomResponse
    check_in_date: date
    check_out_date: date
    nights_count: int
    services: List[ServiceResponse]
    status: str
    total_price: float
    used_bonus_points: float
    earned_bonus_points: float
    created_at: datetime


class UpdateBookingStatusRequest(BaseModel):
    status: str = Field(..., description="Новий статус (created, confirmed, checked_in, checked_out, cancelled)")


# --- Admin Report Schemas ---

class FinancialReportResponse(BaseModel):
    total_bookings: int
    total_revenue: float
    avg_booking_value: float
    monthly_revenue: List[dict]
    revenue_by_category: List[dict]


class OccupancyReportResponse(BaseModel):
    total_rooms: int
    available_rooms: int
    occupied_rooms: int
    occupancy_rate_percentage: float
