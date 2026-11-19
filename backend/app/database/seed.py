"""
Скрипт початкового наповнення бази даних (Seed Data).
Створює початковий номерний фонд (економ, стандарт, люкс), додаткові сервіси,
тестових користувачів (клієнтів та адміністратора) і зразки бронювань.
"""

from datetime import date, datetime, timedelta
import os
import sys

# Додаємо корінь backend у sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database.connection import DatabaseManager, db_manager
from app.domain.factories.room_factory import RoomFactoryProvider
from app.domain.models.entities import AdditionalService, Booking, User
from app.domain.models.enums import (
    Amenity,
    BookingStatus,
    LoyaltyTier,
    RoomStatus,
    RoomType,
    ServiceType,
    UserRole,
)
from app.repositories import (
    BookingRepository,
    RoomRepository,
    ServiceRepository,
    UserRepository,
)


def seed_database(manager: DatabaseManager = db_manager):
    """
    Наповнює базу даних демонстраційними записами.
    Скрипт можна запускати повторно: перед наповненням усі дані видаляються,
    а дати бронювань рахуються від поточного дня.
    """
    print("Ініціалізація схеми бази даних...")
    manager.init_db()
    manager.clear_all()

    room_repo = RoomRepository(manager)
    user_repo = UserRepository(manager)
    service_repo = ServiceRepository(manager)
    booking_repo = BookingRepository(manager, user_repo, room_repo, service_repo)

    # 1. Створюємо користувачів
    print("Створення користувачів...")
    admin = User(
        id="usr-admin-01",
        full_name="Олександр Петренко (Головний адміністратор)",
        email="admin@hotel.ua",
        phone="+380322001122",
        role=UserRole.ADMIN,
        loyalty_tier=LoyaltyTier.PLATINUM,
        bonus_points=0.0,
    )
    client_1 = User(
        id="usr-client-01",
        full_name="Іван Франко",
        email="ivan.franko@example.ua",
        phone="+380501234567",
        role=UserRole.CLIENT,
        loyalty_tier=LoyaltyTier.GOLD,
        bonus_points=450.0,
    )
    client_2 = User(
        id="usr-client-02",
        full_name="Леся Українка",
        email="lesya.ukrainka@example.ua",
        phone="+380679876543",
        role=UserRole.CLIENT,
        loyalty_tier=LoyaltyTier.PLATINUM,
        bonus_points=1200.0,
    )
    user_repo.save(admin)
    user_repo.save(client_1)
    user_repo.save(client_2)

    # 2. Створюємо додаткові сервіси
    print("Створення додаткових послуг...")
    services = [
        AdditionalService(
            id="srv-meal-01",
            name="Сніданок «Шведський стіл»",
            service_type=ServiceType.MEAL,
            price=250.0,
            description="Щоденний багатий сніданок з гарячими стравами, випічкою та натуральною кавою.",
        ),
        AdditionalService(
            id="srv-transfer-01",
            name="VIP Трансфер (Аеропорт / Вокзал)",
            service_type=ServiceType.TRANSFER,
            price=500.0,
            description="Комфортабельний трансфер бізнес-класу з водієм безпосередньо до готелю.",
        ),
        AdditionalService(
            id="srv-spa-01",
            name="Безлімітний SPA & Wellness",
            service_type=ServiceType.SPA,
            price=700.0,
            description="Доступ до сауни, джакузі, басейну з підігрівом та зони релаксації.",
        ),
        AdditionalService(
            id="srv-cleaning-01",
            name="Експрес-хімчистка та прасування",
            service_type=ServiceType.CLEANING,
            price=350.0,
            description="Швидкий догляд за одягом гостя протягом 3 годин.",
        ),
    ]
    for s in services:
        service_repo.save(s)

    # 3. Створюємо номерний фонд через фабрику
    print("Створення номерного фонду...")
    rooms_data = [
        # Економ номери
        (
            RoomType.ECONOMY,
            "101",
            650.0,
            1,
            "Компактний одномісний номер економ-класу з робочим куточком та Wi-Fi.",
            {Amenity.WIFI, Amenity.TV},
            ["https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=600"],
        ),
        (
            RoomType.ECONOMY,
            "102",
            800.0,
            2,
            "Двомісний економ-номер з роздільними ліжками та смарт-телевізором.",
            {Amenity.WIFI, Amenity.TV, Amenity.WORK_DESK},
            ["https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=600"],
        ),
        # Стандарт номери
        (
            RoomType.STANDARD,
            "201",
            1200.0,
            2,
            "Класичний двомісний номер із великим двоспальним ліжком, кондиціонером і сейфом.",
            {Amenity.WIFI, Amenity.TV, Amenity.AIR_CONDITIONING, Amenity.SAFE, Amenity.CITY_VIEW},
            ["https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=600"],
        ),
        (
            RoomType.STANDARD,
            "202",
            1350.0,
            3,
            "Сімейний тримісний номер з кондиціонером, робочою зоною та видом на місто.",
            {Amenity.WIFI, Amenity.TV, Amenity.AIR_CONDITIONING, Amenity.SAFE, Amenity.WORK_DESK, Amenity.CITY_VIEW},
            ["https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600"],
        ),
        (
            RoomType.STANDARD,
            "203",
            1250.0,
            2,
            "Затишний стандарт на другому поверсі з панорамними вікнами.",
            {Amenity.WIFI, Amenity.TV, Amenity.AIR_CONDITIONING, Amenity.SAFE, Amenity.CITY_VIEW},
            ["https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=600"],
        ),
        # Люкс номери
        (
            RoomType.DELUXE,
            "301",
            2500.0,
            3,
            "Люкс-апартаменти з балконом, персональним джакузі, міні-баром та чудовим видом на гори.",
            {Amenity.WIFI, Amenity.TV, Amenity.AIR_CONDITIONING, Amenity.SAFE, Amenity.BALCONY, Amenity.MINI_BAR, Amenity.JACUZZI, Amenity.MOUNTAIN_VIEW},
            ["https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600"],
        ),
        (
            RoomType.DELUXE,
            "302",
            2800.0,
            4,
            "Президентський двокімнатний люкс із терасою, дизайнерським інтер'єром та гідромасажем.",
            {Amenity.WIFI, Amenity.TV, Amenity.AIR_CONDITIONING, Amenity.SAFE, Amenity.BALCONY, Amenity.MINI_BAR, Amenity.JACUZZI, Amenity.MOUNTAIN_VIEW, Amenity.WORK_DESK},
            ["https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=600"],
        ),
    ]

    saved_rooms = []
    for r_type, number, price, capacity, desc, amenities, photos in rooms_data:
        room = RoomFactoryProvider.create_room(
            room_type=r_type,
            room_number=number,
            base_price=price,
            capacity=capacity,
            description=desc,
            amenities=amenities,
            photo_urls=photos,
        )
        saved_rooms.append(room_repo.save(room))

    # 4. Створюємо зразки бронювань
    print("Створення зразків бронювань...")
    today = date.today()
    booking_1 = Booking(
        id="bk-sample-01",
        guest=client_1,
        room=saved_rooms[2],  # Номер 201
        check_in_date=today + timedelta(days=2),
        check_out_date=today + timedelta(days=5),
        services=[services[0], services[2]],  # сніданок + SPA
        status=BookingStatus.CONFIRMED,
        total_price=5250.0,
        used_bonus_points=50.0,
        created_at=datetime.now() - timedelta(days=1),
    )
    booking_2 = Booking(
        id="bk-sample-02",
        guest=client_2,
        room=saved_rooms[5],  # Люкс 301
        check_in_date=today + timedelta(days=7),
        check_out_date=today + timedelta(days=11),
        services=[services[0], services[1], services[2]],
        status=BookingStatus.CREATED,
        total_price=11200.0,
        used_bonus_points=200.0,
        created_at=datetime.now(),
    )
    booking_repo.create(booking_1)
    booking_repo.create(booking_2)

    print("✅ Базу даних успішно ініціалізовано та наповнено початковими даними!")


if __name__ == "__main__":
    seed_database()
