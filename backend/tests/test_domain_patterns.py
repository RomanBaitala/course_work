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
)
from app.domain.pricing.service_decorator import (
    BaseRoomStay,
    BreakfastDecorator,
    CustomServiceDecorator,
    SpaPackageDecorator,
    TransferDecorator,
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

    def test_base_room_stay_cost(self):
        # 1200 * 3 = 3600
        self.assertEqual(self.base_stay.calculate_cost(), 3600.0)
        self.assertIn("Проживання в номері 305", self.base_stay.get_description())

    def test_breakfast_decorator(self):
        # 3600 + (250 * 2 гості * 3 доби) = 3600 + 1500 = 5100
        decorated = BreakfastDecorator(self.base_stay, price_per_day=250.0, guests_count=2)
        self.assertEqual(decorated.calculate_cost(), 5100.0)
        self.assertIn("Сніданок (шведський стіл, 2 ос.): 1500.0 грн", decorated.get_description())

    def test_multiple_decorators_layering(self):
        # Базове проживання 3600
        # + Сніданок (1 гість, 3 доби) = 750
        # + Трансфер = 400
        # + SPA = 700
        # Всього = 3600 + 750 + 400 + 700 = 5450 грн
        decorated = SpaPackageDecorator(
            TransferDecorator(
                BreakfastDecorator(self.base_stay, price_per_day=250.0, guests_count=1),
                transfer_price=400.0,
            ),
            spa_price=700.0,
        )

        self.assertEqual(decorated.calculate_cost(), 5450.0)
        desc = decorated.get_description()
        self.assertIn("Проживання в номері 305", desc)
        self.assertIn("Сніданок", desc)
        self.assertIn("Трансфер", desc)
        self.assertIn("SPA", desc)

    def test_custom_service_decorator(self):
        excursion = AdditionalService(
            name="Екскурсія замками Львова",
            service_type=ServiceType.EXCURSION,
            price=450.0,
        )
        decorated = CustomServiceDecorator(self.base_stay, excursion)
        self.assertEqual(decorated.calculate_cost(), 4050.0)
        self.assertIn("Екскурсія замками Львова: 450.0 грн", decorated.get_description())


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


if __name__ == "__main__":
    unittest.main()
