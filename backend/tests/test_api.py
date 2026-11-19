"""
Тести для REST API системи управління готелем.
Перевіряють роботу обробників запитів, фільтрацію номерів, створення бронювань,
валідацію зайнятості дат та формування адмін-звітів.

Тести працюють з окремою тимчасовою БД, яку перед кожним тестом заново наповнює seed.py,
тому не змінюють робочу hotel.db і не залежать від дня, коли її наповнювали.
"""

from contextlib import redirect_stdout
from datetime import date, timedelta
import io
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_DIR = os.path.join(BASE_DIR, "libs")
if LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import HTTPException

from app.api.v1.admin import (
    get_all_hotel_bookings,
    get_financial_report,
    get_occupancy_report,
    update_booking_status,
)
from app.api.v1.bookings import cancel_booking, create_booking, get_my_bookings
from app.api.v1.rooms import get_room_by_id, get_rooms
from app.api.v1.schemas import CreateBookingRequest, UpdateBookingStatusRequest
from app.api.v1.services import get_services
from app.api.v1.users import get_users
from app.database.connection import db_manager
from app.database.seed import seed_database
from app.domain.models.enums import BookingStatus, RoomType
from app.repositories import RoomRepository, UserRepository


class TestHotelAPI(unittest.TestCase):
    """Інтеграційні тести функціоналу REST API."""

    @classmethod
    def setUpClass(cls):
        # Перенаправляємо глобальний менеджер БД (його використовують усі репозиторії API)
        # на тимчасовий файл і повертаємо назад після тестів.
        fd, cls.test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls.original_db_path = db_manager.db_path
        db_manager.db_path = cls.test_db_path

    @classmethod
    def tearDownClass(cls):
        db_manager.db_path = cls.original_db_path
        os.remove(cls.test_db_path)

    def setUp(self):
        with redirect_stdout(io.StringIO()):
            seed_database(db_manager)
        self.room_repo = RoomRepository()
        self.user_repo = UserRepository()
        self.users = get_users()
        self.rooms = get_rooms()

    def test_get_rooms_returns_catalog(self):
        rooms = get_rooms()
        self.assertGreaterEqual(len(rooms), 7)
        numbers = [r.room_number for r in rooms]
        self.assertIn("101", numbers)
        self.assertIn("201", numbers)
        self.assertIn("301", numbers)

    def test_filter_rooms_by_type(self):
        deluxe_rooms = get_rooms(room_type=RoomType.DELUXE)
        self.assertGreaterEqual(len(deluxe_rooms), 2)
        for r in deluxe_rooms:
            self.assertEqual(r.room_type, "deluxe")

    def test_filter_rooms_by_price(self):
        budget_rooms = get_rooms(max_price=1000.0)
        for r in budget_rooms:
            self.assertLessEqual(r.base_price_per_night, 1000.0)

    def test_get_room_by_id(self):
        target = self.rooms[0]
        room = get_room_by_id(target.id)
        self.assertEqual(room.id, target.id)
        self.assertEqual(room.room_number, target.room_number)

    def test_get_services_catalog(self):
        services = get_services()
        self.assertGreaterEqual(len(services), 4)
        names = [s.name for s in services]
        self.assertTrue(any("Сніданок" in name for name in names))

    def test_create_booking_successfully(self):
        client = self.users[0]
        # Беремо вільну кімнату на майбутні дати
        free_room = self.room_repo.get_by_number("102")
        today = date.today()
        future_in = today + timedelta(days=40)
        future_out = today + timedelta(days=43)

        services = get_services()
        req = CreateBookingRequest(
            guest_id=client.id,
            room_id=free_room.id,
            check_in_date=future_in,
            check_out_date=future_out,
            service_ids=[services[0].id],
            use_bonus_points=0.0,
        )

        res = create_booking(req)
        self.assertEqual(res.room.room_number, "102")
        self.assertEqual(res.nights_count, 3)
        self.assertEqual(res.status, "created")
        self.assertGreater(res.total_price, 0)

    def test_create_booking_rejects_overlapping_dates(self):
        client = self.users[0]
        # Кімната 201 вже заброньована на дати (today + 2 до today + 5) через seed.py
        room_201 = self.room_repo.get_by_number("201")
        today = date.today()

        req = CreateBookingRequest(
            guest_id=client.id,
            room_id=room_201.id,
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=4),
            service_ids=[],
        )

        # Очікуємо конфлікт 409
        with self.assertRaises(HTTPException) as ctx:
            create_booking(req)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_admin_financial_report(self):
        report = get_financial_report()
        self.assertGreaterEqual(report.total_bookings, 2)
        self.assertGreater(report.total_revenue, 0)
        self.assertTrue(len(report.revenue_by_category) > 0)

    def test_admin_occupancy_report(self):
        report = get_occupancy_report()
        self.assertGreaterEqual(report.total_rooms, 7)
        self.assertGreaterEqual(report.available_rooms, 1)

    def test_cancel_booking(self):
        # Створюємо нову бронь і потім скасовуємо її
        client = self.users[0]
        room = self.room_repo.get_by_number("101")
        today = date.today()

        req = CreateBookingRequest(
            guest_id=client.id,
            room_id=room.id,
            check_in_date=today + timedelta(days=60),
            check_out_date=today + timedelta(days=62),
        )
        booking = create_booking(req)

        cancel_res = cancel_booking(booking.id)
        self.assertEqual(cancel_res["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
