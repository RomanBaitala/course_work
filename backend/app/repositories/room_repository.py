"""
Репозиторій для роботи з готельними номерами в базі даних (RoomRepository).
"""

import json
from typing import List, Optional, Set

from app.database.connection import DatabaseManager, db_manager
from app.domain.models.entities import Room
from app.domain.models.enums import Amenity, RoomStatus, RoomType


class RoomRepository:
    """Клас для збереження, отримання та фільтрації номерів готелю."""

    def __init__(self, manager: DatabaseManager = db_manager):
        self.manager = manager

    def _row_to_entity(self, row) -> Room:
        """Перетворює рядок бази даних у доменний об'єкт Room."""
        raw_amenities = json.loads(row["amenities"])
        amenities: Set[Amenity] = {Amenity(a) for a in raw_amenities if a in Amenity._value2member_map_}
        photo_urls = json.loads(row["photo_urls"])

        return Room(
            id=row["id"],
            room_number=row["room_number"],
            room_type=RoomType(row["room_type"]),
            base_price_per_night=float(row["base_price_per_night"]),
            capacity=int(row["capacity"]),
            description=row["description"],
            amenities=amenities,
            status=RoomStatus(row["status"]),
            photo_urls=photo_urls,
        )

    def get_by_id(self, room_id: str) -> Optional[Room]:
        """Отримує номер за його ідентифікатором."""
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_by_number(self, room_number: str) -> Optional[Room]:
        """Отримує номер за номером кімнати (напр. '201')."""
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM rooms WHERE room_number = ?", (room_number,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def save(self, room: Room) -> Room:
        """Зберігає новий або оновлює існуючий номер."""
        amenities_json = json.dumps([a.value for a in room.amenities], ensure_ascii=False)
        photos_json = json.dumps(room.photo_urls, ensure_ascii=False)

        with self.manager.connection() as conn:
            conn.execute(
                """
                INSERT INTO rooms (id, room_number, room_type, base_price_per_night, capacity, description, amenities, status, photo_urls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    room_number = excluded.room_number,
                    room_type = excluded.room_type,
                    base_price_per_night = excluded.base_price_per_night,
                    capacity = excluded.capacity,
                    description = excluded.description,
                    amenities = excluded.amenities,
                    status = excluded.status,
                    photo_urls = excluded.photo_urls;
                """,
                (
                    room.id,
                    room.room_number,
                    room.room_type.value,
                    room.base_price_per_night,
                    room.capacity,
                    room.description,
                    amenities_json,
                    room.status.value,
                    photos_json,
                ),
            )
        return room

    def get_all(
        self,
        room_type: Optional[RoomType] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_capacity: Optional[int] = None,
        amenity: Optional[Amenity] = None,
        only_available: bool = False,
    ) -> List[Room]:
        """Повертає список номерів із гнучкою фільтрацією."""
        query = "SELECT * FROM rooms WHERE 1=1"
        params = []

        if room_type:
            query += " AND room_type = ?"
            params.append(room_type.value)
        if min_price is not None:
            query += " AND base_price_per_night >= ?"
            params.append(min_price)
        if max_price is not None:
            query += " AND base_price_per_night <= ?"
            params.append(max_price)
        if min_capacity is not None:
            query += " AND capacity >= ?"
            params.append(min_capacity)
        if only_available:
            query += " AND status = ?"
            params.append(RoomStatus.AVAILABLE.value)

        query += " ORDER BY base_price_per_night ASC;"

        with self.manager.connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            rooms = [self._row_to_entity(r) for r in rows]

            if amenity:
                rooms = [r for r in rooms if r.has_amenity(amenity)]

            return rooms

    def update_status(self, room_id: str, status: RoomStatus) -> bool:
        """Оновлює експлуатаційний статус номера."""
        with self.manager.connection() as conn:
            cursor = conn.execute(
                "UPDATE rooms SET status = ? WHERE id = ?", (status.value, room_id)
            )
            return cursor.rowcount > 0
