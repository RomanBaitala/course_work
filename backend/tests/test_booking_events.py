"""
Модульні тести патерну Observer: BookingEventManager та слухачі подій бронювання.
Репозиторії замінено простими заглушками в пам'яті, тому БД не використовується.
"""

from datetime import date, timedelta
import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.domain.events import (
    AuditLogListener,
    BookingEvent,
    BookingEventListener,
    BookingEventManager,
    BookingEventType,
    LoyaltyBonusListener,
    NotificationListener,
    RoomStatusListener,
)
from app.domain.factories.room_factory import RoomFactoryProvider
from app.domain.models.entities import Booking, User
from app.domain.models.enums import LoyaltyTier, RoomStatus, RoomType

TODAY = date.today()


class FakeUserRepo:
    def __init__(self, *users):
        self.users = {u.id: u for u in users}

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def save(self, user):
        self.users[user.id] = user
        return user


class FakeBookingRepo:
    def __init__(self, completed=0):
        self.completed = completed

    def count_completed_by_guest(self, guest_id):
        return self.completed


class FakeRoomRepo:
    def __init__(self):
        self.statuses = {}

    def update_status(self, room_id, status):
        self.statuses[room_id] = status
        return True


class SpyListener(BookingEventListener):
    def __init__(self):
        self.received = []

    def update(self, event):
        self.received.append(event.event_type)


def make_booking(guest=None, used=0.0, earned=0.0) -> Booking:
    guest = guest or User(id="g1", full_name="Гість", email="g@test.ua", phone="+380000000000")
    room = RoomFactoryProvider.create_room(RoomType.STANDARD, "201")
    return Booking(guest=guest, room=room, check_in_date=TODAY, check_out_date=TODAY + timedelta(days=2),
                   total_price=2000.0, used_bonus_points=used, earned_bonus_points=earned)


class TestEventManager(unittest.TestCase):

    def test_listener_receives_only_subscribed_events(self):
        mgr, spy = BookingEventManager(), SpyListener()
        mgr.subscribe(spy, BookingEventType.CANCELLED)
        mgr.notify(BookingEvent(BookingEventType.CREATED, make_booking()))
        mgr.notify(BookingEvent(BookingEventType.CANCELLED, make_booking()))
        self.assertEqual(spy.received, [BookingEventType.CANCELLED])

    def test_wildcard_subscription_and_unsubscribe(self):
        mgr, audit = BookingEventManager(), AuditLogListener()
        mgr.subscribe(audit)  # на всі події
        mgr.notify(BookingEvent(BookingEventType.CREATED, make_booking()))
        mgr.unsubscribe(audit)
        mgr.notify(BookingEvent(BookingEventType.CONFIRMED, make_booking()))
        self.assertEqual(len(audit.records), 1)

    def test_duplicate_subscription_ignored(self):
        mgr, spy = BookingEventManager(), SpyListener()
        mgr.subscribe(spy)
        mgr.subscribe(spy)
        mgr.notify(BookingEvent(BookingEventType.CREATED, make_booking()))
        self.assertEqual(len(spy.received), 1)


class TestListeners(unittest.TestCase):

    def test_notification_sent_by_email_and_sms(self):
        n = NotificationListener()
        n.update(BookingEvent(BookingEventType.CONFIRMED, make_booking()))
        self.assertEqual({m.channel for m in n.outbox}, {"email", "sms"})
        self.assertEqual(n.outbox[0].subject, "Бронювання підтверджено")

    def test_cashback_credited_on_check_out(self):
        guest = User(id="g1", bonus_points=100.0)
        listener = LoyaltyBonusListener(FakeUserRepo(guest), FakeBookingRepo(completed=1))
        listener.update(BookingEvent(BookingEventType.CHECKED_OUT, make_booking(guest, earned=60.0)))
        self.assertEqual(guest.bonus_points, 160.0)

    def test_loyalty_tier_upgraded_after_enough_stays(self):
        guest = User(id="g1", loyalty_tier=LoyaltyTier.STANDARD)
        listener = LoyaltyBonusListener(FakeUserRepo(guest), FakeBookingRepo(completed=5))
        listener.update(BookingEvent(BookingEventType.CHECKED_OUT, make_booking(guest)))
        self.assertEqual(guest.loyalty_tier, LoyaltyTier.GOLD)

    def test_loyalty_tier_never_downgraded(self):
        guest = User(id="g1", loyalty_tier=LoyaltyTier.PLATINUM)
        listener = LoyaltyBonusListener(FakeUserRepo(guest), FakeBookingRepo(completed=0))
        listener.update(BookingEvent(BookingEventType.CHECKED_OUT, make_booking(guest)))
        self.assertEqual(guest.loyalty_tier, LoyaltyTier.PLATINUM)

    def test_used_bonuses_refunded_on_cancel(self):
        guest = User(id="g1", bonus_points=50.0)
        listener = LoyaltyBonusListener(FakeUserRepo(guest), FakeBookingRepo())
        listener.update(BookingEvent(BookingEventType.CANCELLED, make_booking(guest, used=200.0)))
        self.assertEqual(guest.bonus_points, 250.0)

    def test_room_status_follows_check_in_and_out(self):
        rooms, b = FakeRoomRepo(), make_booking()
        listener = RoomStatusListener(rooms)
        listener.update(BookingEvent(BookingEventType.CHECKED_IN, b))
        self.assertEqual(rooms.statuses[b.room.id], RoomStatus.OCCUPIED)
        listener.update(BookingEvent(BookingEventType.CHECKED_OUT, b))
        self.assertEqual(rooms.statuses[b.room.id], RoomStatus.AVAILABLE)


if __name__ == "__main__":
    unittest.main()
