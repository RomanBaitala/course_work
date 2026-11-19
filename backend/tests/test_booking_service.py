"""
Тести BookingService: створення бронювання, бонуси, зміна статусів через State
та реакції слухачів подій. Працюють з окремою тимчасовою БД.
"""

from datetime import date, timedelta
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database.connection import DatabaseManager
from app.domain.factories.room_factory import RoomFactoryProvider
from app.domain.models.entities import AdditionalService, User
from app.domain.models.enums import BookingStatus, LoyaltyTier, RoomStatus, RoomType, ServiceType
from app.services.booking_service import (
    BookingError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    RoomUnavailableError,
    create_booking_service,
)

TODAY = date.today()
# Найближчий понеділок, щоб короткі тестові бронювання не потрапляли на тариф вихідного дня
MONDAY = TODAY + timedelta(days=(7 - TODAY.weekday()) % 7 or 7)


class TestBookingService(unittest.TestCase):

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.service = create_booking_service(DatabaseManager(self.db_path))
        self.users, self.rooms, self.bookings = self.service.users, self.service.rooms, self.service.bookings

        self.users.save(User(id="g1", full_name="Гість", email="g1@test.ua",
                             loyalty_tier=LoyaltyTier.STANDARD, bonus_points=1000.0))
        self.users.save(User(id="g2", full_name="Інший гість", email="g2@test.ua"))
        self.room = self.rooms.save(RoomFactoryProvider.create_room(RoomType.STANDARD, "201", base_price=1000.0))
        self.service.services.save(AdditionalService(id="breakfast", name="Сніданок",
                                                     service_type=ServiceType.MEAL, price=200.0))

    def tearDown(self):
        os.remove(self.db_path)

    def book(self, start=0, nights=2, guest_id="g1", **kwargs):
        check_in = MONDAY + timedelta(days=start)
        return self.service.create_booking(guest_id, self.room.id, check_in,
                                           check_in + timedelta(days=nights), **kwargs)

    # ------------------------------------------------------------ створення ---

    def test_price_includes_services_per_night(self):
        b = self.book(nights=2, service_ids=["breakfast"])
        self.assertEqual(b.total_price, 2400.0)  # 2 × 1000 + сніданок 2 × 200
        self.assertEqual(b.status, BookingStatus.CREATED)

    def test_bonuses_deducted_but_cashback_not_credited_on_create(self):
        b = self.book(bonus_to_use=300)
        self.assertEqual(b.used_bonus_points, 300.0)
        self.assertEqual(b.total_price, 1700.0)
        # списано 300, кешбек ще не нараховано
        self.assertEqual(self.users.get_by_id("g1").bonus_points, 700.0)

    def test_bonus_cannot_exceed_balance(self):
        b = self.book(guest_id="g2", bonus_to_use=500)
        self.assertEqual(b.used_bonus_points, 0.0)

    def test_overlapping_dates_rejected(self):
        self.book(start=0, nights=3)
        with self.assertRaises(RoomUnavailableError):
            self.book(start=1, nights=1, guest_id="g2")

    def test_past_check_in_rejected(self):
        with self.assertRaises(BookingError):
            self.service.create_booking("g1", self.room.id, TODAY - timedelta(days=3), TODAY - timedelta(days=1))

    def test_unknown_service_rejected(self):
        with self.assertRaises(NotFoundError):
            self.book(service_ids=["no-such-service"])

    def test_guest_notified_on_create(self):
        self.book()
        self.assertTrue(any(n.subject == "Бронювання прийнято" for n in self.service.notifier.outbox))

    # ----------------------------------------------------------- скасування ---

    def test_cancel_refunds_used_bonuses(self):
        b = self.book(bonus_to_use=300)
        self.service.cancel_booking(b.id, guest_id="g1")
        self.assertEqual(self.users.get_by_id("g1").bonus_points, 1000.0)
        self.assertEqual(self.bookings.get_by_id(b.id).status, BookingStatus.CANCELLED)

    def test_cannot_cancel_someone_elses_booking(self):
        b = self.book()
        with self.assertRaises(ForbiddenError):
            self.service.cancel_booking(b.id, guest_id="g2")

    def test_cancel_and_rebook_does_not_farm_bonuses(self):
        for _ in range(3):
            b = self.book()
            self.service.cancel_booking(b.id)
        self.assertEqual(self.users.get_by_id("g1").bonus_points, 1000.0)

    # ------------------------------------------------- повний цикл (State) ---

    def test_full_cycle_credits_cashback_and_frees_room(self):
        b = self.service.create_booking("g1", self.room.id, TODAY, TODAY + timedelta(days=2))
        self.service.change_status(b.id, "confirm")
        self.service.change_status(b.id, "check_in")
        self.assertEqual(self.rooms.get_by_id(self.room.id).status, RoomStatus.OCCUPIED)

        self.service.change_status(b.id, "check_out")
        self.assertEqual(self.rooms.get_by_id(self.room.id).status, RoomStatus.AVAILABLE)
        self.assertEqual(self.bookings.get_by_id(b.id).status, BookingStatus.CHECKED_OUT)
        # кешбек 3% (Standard) нараховано лише після виселення
        self.assertAlmostEqual(self.users.get_by_id("g1").bonus_points, 1000.0 + b.earned_bonus_points)

    def test_invalid_transition_rejected(self):
        b = self.book()
        with self.assertRaises(InvalidTransitionError):
            self.service.change_status(b.id, "check_out")

    def test_cannot_check_in_cancelled_booking(self):
        b = self.book()
        self.service.cancel_booking(b.id)
        with self.assertRaises(InvalidTransitionError):
            self.service.change_status(b.id, "check_in")

    def test_allowed_actions_follow_state(self):
        b = self.book()
        self.assertEqual(self.service.allowed_actions(b), ["confirm", "cancel", "extend"])
        self.service.change_status(b.id, "cancel")
        self.assertEqual(self.service.allowed_actions(self.bookings.get_by_id(b.id)), [])


if __name__ == "__main__":
    unittest.main()
