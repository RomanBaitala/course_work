"""
Модульні тести патерну State: життєвий цикл бронювання (BookingLifecycle).
Перевіряють дозволені переходи та заборону невалідних (напр. заселити скасоване бронювання).
"""

from datetime import date, timedelta
import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.domain.booking import BookingLifecycle, InvalidStateTransitionError
from app.domain.factories.room_factory import RoomFactoryProvider
from app.domain.models.entities import Booking, User
from app.domain.models.enums import BookingStatus, RoomType

TODAY = date.today()


def make_booking(status=BookingStatus.CREATED) -> Booking:
    room = RoomFactoryProvider.create_room(RoomType.STANDARD, "999")
    return Booking(guest=User(full_name="Тест"), room=room,
                   check_in_date=TODAY + timedelta(days=1),
                   check_out_date=TODAY + timedelta(days=3), status=status)


# =================================================================== State ===

class TestBookingStatePattern(unittest.TestCase):

    def test_happy_path_created_to_checked_out(self):
        b = make_booking()
        lc = BookingLifecycle(b)
        lc.confirm()
        lc.check_in(today=b.check_in_date)
        lc.check_out()
        self.assertEqual(b.status, BookingStatus.CHECKED_OUT)
        self.assertEqual(lc.history, [BookingStatus.CREATED, BookingStatus.CONFIRMED,
                                      BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT])

    def test_cannot_check_in_cancelled_booking(self):
        lc = BookingLifecycle(make_booking())
        lc.cancel()
        with self.assertRaises(InvalidStateTransitionError):
            lc.check_in()

    def test_cannot_check_in_without_confirmation(self):
        with self.assertRaises(InvalidStateTransitionError):
            BookingLifecycle(make_booking()).check_in()

    def test_cannot_cancel_after_check_in(self):
        lc = BookingLifecycle(make_booking(BookingStatus.CHECKED_IN))
        with self.assertRaises(InvalidStateTransitionError):
            lc.cancel()

    def test_final_states_have_no_actions(self):
        for st in (BookingStatus.CHECKED_OUT, BookingStatus.CANCELLED):
            self.assertEqual(BookingLifecycle(make_booking(st)).allowed_actions(), [])

    def test_extend_moves_check_out_date(self):
        b = make_booking(BookingStatus.CHECKED_IN)
        new_out = b.check_out_date + timedelta(days=2)
        BookingLifecycle(b).extend(new_out)
        self.assertEqual(b.check_out_date, new_out)

    def test_extend_rejects_earlier_date(self):
        b = make_booking()
        with self.assertRaises(ValueError):
            BookingLifecycle(b).extend(b.check_out_date - timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
