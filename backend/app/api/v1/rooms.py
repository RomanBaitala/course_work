"""
Endpoints for Hotel Rooms catalog and filtering.
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.schemas import RoomResponse
from app.domain.models.enums import Amenity, RoomType
from app.repositories import RoomRepository

router = APIRouter(prefix="/rooms", tags=["Rooms Catalog"])
room_repo = RoomRepository()


def _entity_to_response(r) -> RoomResponse:
    return RoomResponse(
        id=r.id,
        room_number=r.room_number,
        room_type=r.room_type.value,
        base_price_per_night=r.base_price_per_night,
        capacity=r.capacity,
        description=r.description,
        amenities=[a.value for a in r.amenities],
        status=r.status.value,
        photo_urls=r.photo_urls,
    )


@router.get("", response_model=List[RoomResponse], summary="Отримати каталог номерів із фільтрацією")
def get_rooms(
    room_type: Optional[RoomType] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    capacity: Optional[int] = None,
    amenity: Optional[Amenity] = None,
    only_available: bool = False,
):
    """Повертає перелік готельних номерів, що відповідають критеріям пошуку."""
    rooms = room_repo.get_all(
        room_type=room_type,
        min_price=min_price,
        max_price=max_price,
        min_capacity=capacity,
        amenity=amenity,
        only_available=only_available,
    )
    return [_entity_to_response(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse, summary="Деталі конкретного номера за ID")
def get_room_by_id(room_id: str):
    room = room_repo.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Номер з ID '{room_id}' не знайдено.")
    return _entity_to_response(room)
