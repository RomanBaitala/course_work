"""
Репозиторій для роботи з бронюваннями (BookingRepository).
Включає перевірку доступності номерів на задані дати та агрегацію аналітики для адмін-панелі.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.database.connection import DatabaseManager, db_manager
from app.domain.models.entities import AdditionalService, Booking, Room, User
from app.domain.models.enums import BookingStatus
from app.repositories.room_repository import RoomRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.user_repository import UserRepository


class BookingRepository:
    """Клас для збереження, валідації перетинів та аналітики бронювань."""

    def __init__(
        self,
        manager: DatabaseManager = db_manager,
        user_repo: Optional[UserRepository] = None,
        room_repo: Optional[RoomRepository] = None,
        service_repo: Optional[ServiceRepository] = None,
    ):
        self.manager = manager
        self.user_repo = user_repo or UserRepository(manager)
        self.room_repo = room_repo or RoomRepository(manager)
        self.service_repo = service_repo or ServiceRepository(manager)

    def is_room_available(
        self,
        room_id: str,
        check_in_date: date,
        check_out_date: date,
        exclude_booking_id: Optional[str] = None,
    ) -> bool:
        """
        Перевіряє, чи вільний номер на вказані дати.
        Умова перетину періодів: (check_in_date < existing_checkout) AND (check_out_date > existing_checkin)
        для всіх активних бронювань (не скасованих).
        """
        query = """
        SELECT COUNT(*) as count FROM bookings
        WHERE room_id = ?
          AND status NOT IN ('cancelled', 'checked_out')
          AND check_in_date < ?
          AND check_out_date > ?
        """
        params = [room_id, check_out_date.isoformat(), check_in_date.isoformat()]

        if exclude_booking_id:
            query += " AND id != ?"
            params.append(exclude_booking_id)

        with self.manager.connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return (row["count"] if row else 0) == 0

    def create(self, booking: Booking) -> Booking:
        """Зберігає нове бронювання разом із пов'язаними послугами в одній транзакції."""
        with self.manager.connection() as conn:
            conn.execute(
                """
                INSERT INTO bookings (
                    id, guest_id, room_id, check_in_date, check_out_date,
                    status, total_price, used_bonus_points, earned_bonus_points, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    booking.id,
                    booking.guest.id,
                    booking.room.id,
                    booking.check_in_date.isoformat(),
                    booking.check_out_date.isoformat(),
                    booking.status.value,
                    booking.total_price,
                    booking.used_bonus_points,
                    booking.earned_bonus_points,
                    booking.created_at.isoformat(),
                ),
            )

            # Додаємо зв'язок із замовленими додатковими послугами
            for s in booking.services:
                conn.execute(
                    """
                    INSERT INTO booking_services (booking_id, service_id, price_at_booking)
                    VALUES (?, ?, ?);
                    """,
                    (booking.id, s.id, s.price),
                )

        return booking

    def _build_booking_from_row(self, row, conn) -> Booking:
        """Збирає повний об'єкт Booking із сутностями гостя, номера та списку послуг."""
        guest = self.user_repo.get_by_id(row["guest_id"]) or User(id=row["guest_id"])
        room = self.room_repo.get_by_id(row["room_id"]) or Room(id=row["room_id"])

        # Отримуємо послуги
        cursor = conn.execute(
            """
            SELECT s.* FROM services s
            JOIN booking_services bs ON s.id = bs.service_id
            WHERE bs.booking_id = ?
            """,
            (row["id"],),
        )
        services = [self.service_repo._row_to_entity(r) for r in cursor.fetchall()]

        return Booking(
            id=row["id"],
            guest=guest,
            room=room,
            check_in_date=date.fromisoformat(row["check_in_date"]),
            check_out_date=date.fromisoformat(row["check_out_date"]),
            services=services,
            status=BookingStatus(row["status"]),
            total_price=float(row["total_price"]),
            used_bonus_points=float(row["used_bonus_points"]),
            earned_bonus_points=float(row["earned_bonus_points"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Отримує деталі бронювання за ID."""
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            row = cursor.fetchone()
            return self._build_booking_from_row(row, conn) if row else None

    def get_by_guest_id(self, guest_id: str) -> List[Booking]:
        """Отримує історію бронювань конкретного гостя."""
        with self.manager.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM bookings WHERE guest_id = ? ORDER BY check_in_date DESC;",
                (guest_id,),
            )
            rows = cursor.fetchall()
            return [self._build_booking_from_row(r, conn) for r in rows]

    def get_all(self, status: Optional[BookingStatus] = None) -> List[Booking]:
        """Отримує всі бронювання готелю (з можливістю фільтра за статусом)."""
        query = "SELECT * FROM bookings"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status.value)
        query += " ORDER BY check_in_date DESC;"

        with self.manager.connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._build_booking_from_row(r, conn) for r in rows]

    def update_status(self, booking_id: str, new_status: BookingStatus) -> bool:
        """Оновлює статус бронювання (напр. підтверджено, скасовано, заселено)."""
        with self.manager.connection() as conn:
            cursor = conn.execute(
                "UPDATE bookings SET status = ? WHERE id = ?",
                (new_status.value, booking_id),
            )
            return cursor.rowcount > 0

    def count_completed_by_guest(self, guest_id: str) -> int:
        """Кількість завершених проживань гостя (для програми лояльності)."""
        with self.manager.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM bookings WHERE guest_id = ? AND status = 'checked_out';",
                (guest_id,),
            ).fetchone()
            return int(row["c"])

    # --- Аналітика для адміністратора ---

    def get_financial_summary(self) -> Dict[str, Any]:
        """Повертає загальну виручку, середній чек та кількість активних замовлень."""
        with self.manager.connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_bookings,
                    TOTAL(total_price) as total_revenue,
                    AVG(total_price) as avg_booking_value
                FROM bookings
                WHERE status != 'cancelled';
                """
            )
            summary = dict(cursor.fetchone())

            cursor = conn.execute(
                """
                SELECT strftime('%Y-%m', check_in_date) as month, TOTAL(total_price) as monthly_revenue
                FROM bookings
                WHERE status != 'cancelled'
                GROUP BY month
                ORDER BY month ASC;
                """
            )
            monthly = [dict(r) for r in cursor.fetchall()]

            cursor = conn.execute(
                """
                SELECT r.room_type, COUNT(b.id) as bookings_count, TOTAL(b.total_price) as revenue
                FROM bookings b
                JOIN rooms r ON b.room_id = r.id
                WHERE b.status != 'cancelled'
                GROUP BY r.room_type;
                """
            )
            by_category = [dict(r) for r in cursor.fetchall()]

            return {
                "total_bookings": summary["total_bookings"] or 0,
                "total_revenue": round(summary["total_revenue"] or 0.0, 2),
                "avg_booking_value": round(summary["avg_booking_value"] or 0.0, 2),
                "monthly_revenue": monthly,
                "revenue_by_category": by_category,
            }
