"""
Модульні тести для перевірки доменних моделей та GoF-патернів:
1. Factory Method (створення категорій номерів)
2. Builder & Director (конструювання та валідація бронювань)
3. Decorator (динамічне нашарування послуг)
4. Strategy (алгоритми ціноутворення та знижок)
"""

from datetime import date, timedelta
import os
import sys
import unittest

# Додаємо шлях до backend у sys.path для підтримки імпорту app.*
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.builders.booking_builder import (
    BookingBuildError,
    BookingBuilder,
    BookingDirector,
)
from app.domain.factories.room_factory import (
    DeluxeRoom,
    DeluxeRoomFactory,
    EconomyRoom,
    EconomyRoomFactory,
    RoomFactoryProvider,
    StandardRoom,
    StandardRoomFactory,
)
from app.domain.models.entities import (
    AdditionalService,
    Booking,
    Room,
    User,
)
from app.domain.models.enums import (
    Amenity,
    BookingStatus,
    LoyaltyTier,
    RoomStatus,
    RoomType,
    ServiceType,
    UserRole,
)
from app.domain.pricing.pricing_strategy import (
    LongStayDiscountStrategy,
    LoyaltyPricingStrategy,
    PricingCalculatorContext,
    StandardPricingStrategy,
    WeekendSurchargeStrategy,
    is_weekend_stay,
    select_pricing_strategy,
)
from app.domain.pricing.service_decorator import (
    BaseRoomStay,
    OneTimeServiceDecorator,
    PerNightServiceDecorator,
    build_priced_stay,
)


class TestRoomFactory(unittest.TestCase):
    """Тестування породжувального патерну GoF: Factory Method."""

    def test_economy_room_creation(self):
        factory = EconomyRoomFactory()
        room = factory.create_room(room_number="101")

        self.assertIsInstance(room, EconomyRoom)
        self.assertEqual(room.room_type, RoomType.ECONOMY)
        self.assertEqual(room.room_number, "101")
        self.assertEqual(room.base_price_per_night, 650.0)
        self.assertEqual(room.capacity, 1)
        self.assertTrue(room.has_amenity(Amenity.WIFI))
        self.assertTrue(room.has_amenity(Amenity.TV))
        self.assertFalse(room.has_amenity(Amenity.JACUZZI))

    def test_standard_room_creation(self):
        factory = StandardRoomFactory()
        room = factory.create_room(room_number="205")

        self.assertIsInstance(room, StandardRoom)
        self.assertEqual(room.room_type, RoomType.STANDARD)
        self.assertEqual(room.base_price_per_night, 1200.0)
        self.assertEqual(room.capacity, 2)
        self.assertTrue(room.has_amenity(Amenity.AIR_CONDITIONING))
        self.assertTrue(room.has_amenity(Amenity.SAFE))

    def test_deluxe_room_creation(self):
        factory = DeluxeRoomFactory()
        room = factory.create_room(room_number="501")

        self.assertIsInstance(room, DeluxeRoom)
        self.assertEqual(room.room_type, RoomType.DELUXE)
        self.assertEqual(room.base_price_per_night, 2500.0)
        self.assertTrue(room.has_amenity(Amenity.JACUZZI))
        self.assertTrue(room.has_amenity(Amenity.BALCONY))
        self.assertTrue(room.has_amenity(Amenity.MOUNTAIN_VIEW))

    def test_room_factory_provider(self):
        room = RoomFactoryProvider.create_room(RoomType.DELUXE, "502", base_price=3000.0)
        self.assertEqual(room.room_type, RoomType.DELUXE)
        self.assertEqual(room.base_price_per_night, 3000.0)

    def test_room_factory_provider_invalid_type(self):
        with self.assertRaises(ValueError):
            RoomFactoryProvider.get_factory("UNKNOWN_TYPE")  # type: ignore


class TestBookingBuilder(unittest.TestCase):
    """Тестування породжувального патерну GoF: Builder та BookingDirector."""

    def setUp(self):
        self.builder = BookingBuilder()
        self.guest = User(
            full_name="Тарас Шевченко",
            email="taras@example.ua",
            phone="+380501112233",
            bonus_points=300.0,
        )
        self.room = RoomFactoryProvider.create_room(RoomType.STANDARD, "202")
        self.today = date.today()
        self.tomorrow = self.today + timedelta(days=2)

    def test_successful_booking_build(self):
        booking = (
            self.builder.reset()
            .set_guest(self.guest)
            .set_room(self.room)
            .set_dates(self.today, self.tomorrow)
            .apply_bonus_points(100.0)
            .build()
        )

        self.assertIsInstance(booking, Booking)
        self.assertEqual(booking.guest.full_name, "Тарас Шевченко")
        self.assertEqual(booking.room.room_number, "202")
        self.assertEqual(booking.nights_count, 2)
        self.assertEqual(booking.used_bonus_points, 100.0)
        self.assertEqual(booking.status, BookingStatus.CREATED)

    def test_builder_takes_price_from_pricing_module(self):
        booking = (
            self.builder.reset()
            .set_guest(self.guest)
            .set_room(self.room)
            .set_dates(self.today, self.tomorrow)
            .set_pricing(2300.0, earned_bonus_points=69.0)
            .build()
        )
        # Builder не рахує ціну сам — бере передану модулем ціноутворення
        self.assertEqual(booking.total_price, 2300.0)
        self.assertEqual(booking.earned_bonus_points, 69.0)

    def test_negative_price_rejected(self):
        with self.assertRaises(BookingBuildError):
            self.builder.reset().set_pricing(-1.0)

    def test_booking_validation_dates_chronology(self):
        # Дата виїзду раніше або дорівнює даті заїзду
        with self.assertRaises(BookingBuildError):
            self.builder.reset().set_guest(self.guest).set_room(self.room).set_dates(
                self.tomorrow, self.today
            )

    def test_booking_validation_maintenance_room(self):
        broken_room = RoomFactoryProvider.create_room(RoomType.ECONOMY, "103")
        broken_room.status = RoomStatus.MAINTENANCE

        with self.assertRaises(BookingBuildError):
            self.builder.reset().set_guest(self.guest).set_room(broken_room)

    def test_booking_validation_excessive_bonus_points(self):
        # У гостя 300 бонусів, намагаємось використати 500
        with self.assertRaises(BookingBuildError):
            (
                self.builder.reset()
                .set_guest(self.guest)
                .set_room(self.room)
                .set_dates(self.today, self.tomorrow)
                .apply_bonus_points(500.0)
            )

    def test_booking_director_basic_stay(self):
        booking = BookingDirector.construct_basic_stay(
            self.builder, self.guest, self.room, self.today, self.tomorrow
        )
        self.assertEqual(booking.nights_count, 2)
        self.assertEqual(len(booking.services), 0)

    def test_booking_director_vip_package(self):
        meal = AdditionalService(name="All Inclusive", service_type=ServiceType.MEAL, price=600.0)
        transfer = AdditionalService(name="VIP Transfer", service_type=ServiceType.TRANSFER, price=500.0)
        spa = AdditionalService(name="Full SPA", service_type=ServiceType.SPA, price=800.0)

        booking = BookingDirector.construct_vip_package(
            self.builder, self.guest, self.room, self.today, self.tomorrow, spa, transfer, meal
        )
        self.assertEqual(len(booking.services), 3)
        self.assertEqual({s.service_type for s in booking.services},
                         {ServiceType.MEAL, ServiceType.TRANSFER, ServiceType.SPA})


class TestServiceDecorator(unittest.TestCase):
    """Тестування структурного патерну GoF: Decorator."""

    def setUp(self):
        self.room = RoomFactoryProvider.create_room(RoomType.STANDARD, "305")
        self.base_stay = BaseRoomStay(self.room, nights=3)
        self.breakfast = AdditionalService(name="Сніданок", service_type=ServiceType.MEAL, price=250.0)
        self.transfer = AdditionalService(name="Трансфер", service_type=ServiceType.TRANSFER, price=500.0)
        self.spa = AdditionalService(name="SPA", service_type=ServiceType.SPA, price=700.0)

    def test_base_room_stay_cost(self):
        # 1200 * 3 = 3600
        self.assertEqual(self.base_stay.calculate_cost(), 3600.0)
        self.assertIn("Проживання в номері 305", self.base_stay.get_description())

    def test_meal_is_charged_per_night(self):
        # 3600 + 250 * 3 ночі = 4350
        decorated = PerNightServiceDecorator(self.base_stay, self.breakfast)
        self.assertEqual(decorated.calculate_cost(), 4350.0)
        self.assertEqual(decorated.service_cost(), 750.0)

    def test_one_time_service_charged_once(self):
        decorated = OneTimeServiceDecorator(self.base_stay, self.transfer)
        self.assertEqual(decorated.calculate_cost(), 4100.0)

    def test_multiple_decorators_layering(self):
        # 3600 + сніданок 750 + трансфер 500 + SPA 700 = 5550
        item = build_priced_stay(self.room, 3, [self.breakfast, self.transfer, self.spa])
        self.assertIsInstance(item, OneTimeServiceDecorator)
        self.assertEqual(item.calculate_cost(), 5550.0)
        self.assertEqual(item.nights, 3)
        names = [name for name, _ in item.get_receipt_lines()]
        self.assertEqual(len(names), 4)
        self.assertIn("Проживання в номері 305", names[0])
        self.assertIn("SPA", item.get_description())

    def test_decorator_chosen_by_service_type(self):
        item = build_priced_stay(self.room, 2, [self.breakfast])
        self.assertIsInstance(item, PerNightServiceDecorator)
        excursion = AdditionalService(name="Екскурсія", service_type=ServiceType.EXCURSION, price=450.0)
        self.assertIsInstance(build_priced_stay(self.room, 2, [excursion]), OneTimeServiceDecorator)


class TestPricingStrategy(unittest.TestCase):
    """Тестування поведінкового патерну GoF: Strategy."""

    def setUp(self):
        self.context = PricingCalculatorContext(StandardPricingStrategy())
        self.client_standard = User(full_name="Олег", loyalty_tier=LoyaltyTier.STANDARD)
        self.client_silver = User(full_name="Марія", loyalty_tier=LoyaltyTier.SILVER)
        self.client_gold = User(full_name="Андрій", loyalty_tier=LoyaltyTier.GOLD)
        self.client_platinum = User(full_name="Олена", loyalty_tier=LoyaltyTier.PLATINUM)
        self.base_amount = 10000.0

    def test_standard_pricing_strategy(self):
        res = self.context.calculate(self.base_amount, nights=3, guest=self.client_standard)
        self.assertEqual(res, 10000.0)

    def test_long_stay_discount_strategy(self):
        self.context.strategy = LongStayDiscountStrategy()

        # 3 доби: без знижки
        self.assertEqual(self.context.calculate(self.base_amount, nights=3, guest=self.client_standard), 10000.0)
        # 5 діб: 10% знижки
        self.assertEqual(self.context.calculate(self.base_amount, nights=5, guest=self.client_standard), 9000.0)
        # 8 діб: 15% знижки
        self.assertEqual(self.context.calculate(self.base_amount, nights=8, guest=self.client_standard), 8500.0)

    def test_loyalty_pricing_strategy(self):
        self.context.strategy = LoyaltyPricingStrategy()

        # Standard: 0%
        self.assertEqual(self.context.calculate(self.base_amount, 2, self.client_standard), 10000.0)
        # Silver: 5%
        self.assertEqual(self.context.calculate(self.base_amount, 2, self.client_silver), 9500.0)
        # Gold: 10%
        self.assertEqual(self.context.calculate(self.base_amount, 2, self.client_gold), 9000.0)
        # Platinum: 15%
        self.assertEqual(self.context.calculate(self.base_amount, 2, self.client_platinum), 8500.0)

    def test_weekend_surcharge_strategy(self):
        self.context.strategy = WeekendSurchargeStrategy(surcharge_rate=0.20)
        # +20%
        self.assertEqual(self.context.calculate(self.base_amount, 2, self.client_standard), 12000.0)


class TestPricingStrategySelection(unittest.TestCase):
    """Сервер сам обирає тариф за датами проживання та рівнем лояльності гостя."""

    # 2026-11-20 — п'ятниця
    FRIDAY = date(2026, 11, 20)
    MONDAY = date(2026, 11, 23)

    def setUp(self):
        self.standard = User(full_name="Олег", loyalty_tier=LoyaltyTier.STANDARD)
        self.gold = User(full_name="Андрій", loyalty_tier=LoyaltyTier.GOLD)

    def select(self, check_in, nights, guest):
        return select_pricing_strategy(10000.0, check_in, check_in + timedelta(days=nights), guest)

    def test_weekend_detection(self):
        self.assertTrue(is_weekend_stay(self.FRIDAY, self.FRIDAY + timedelta(days=2)))   # пт–нд
        self.assertFalse(is_weekend_stay(self.FRIDAY, self.FRIDAY + timedelta(days=3)))  # пт–пн (3 ночі)
        self.assertFalse(is_weekend_stay(self.MONDAY, self.MONDAY + timedelta(days=1)))

    def test_short_weekend_stay_gets_surcharge_even_for_loyal_guest(self):
        self.assertIsInstance(self.select(self.FRIDAY, 2, self.gold), WeekendSurchargeStrategy)

    def test_weekday_short_stay_without_discounts_is_standard(self):
        self.assertIsInstance(self.select(self.MONDAY, 2, self.standard), StandardPricingStrategy)

    def test_loyal_guest_gets_loyalty_discount(self):
        self.assertIsInstance(self.select(self.MONDAY, 2, self.gold), LoyaltyPricingStrategy)

    def test_best_discount_wins_for_long_stay(self):
        # 7 ночей: тривале перебування −15% вигідніше за Gold −10%
        self.assertIsInstance(self.select(self.MONDAY, 7, self.gold), LongStayDiscountStrategy)
        # 4 ночі: −10% за тривалість = Gold −10%, береться перша (тривале перебування)
        self.assertIsInstance(self.select(self.MONDAY, 4, self.standard), LongStayDiscountStrategy)


if __name__ == "__main__":
    unittest.main()
