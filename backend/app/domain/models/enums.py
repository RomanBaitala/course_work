"""
Перерахування (Enums) для предметної області "Система управління готелем".
Визначають типи номерів, статуси, зручності, ролі користувачів та рівні лояльності.
"""

from enum import Enum


class RoomType(str, Enum):
    """Категорії номерного фонду готелю."""
    ECONOMY = "economy"      # Економ-клас
    STANDARD = "standard"    # Стандартний номер
    DELUXE = "deluxe"        # Номер підвищеного комфорту / Люкс


class RoomStatus(str, Enum):
    """Поточний експлуатаційний статус номера."""
    AVAILABLE = "available"      # Вільний для бронювання
    BOOKED = "booked"            # Заброньований
    OCCUPIED = "occupied"        # Заселений (гості проживають)
    MAINTENANCE = "maintenance"  # Технічне обслуговування / прибирання


class Amenity(str, Enum):
    """Зручності та оснащення номерів."""
    WIFI = "wi_fi"
    TV = "smart_tv"
    AIR_CONDITIONING = "air_conditioning"
    BALCONY = "balcony"
    MINI_BAR = "mini_bar"
    JACUZZI = "jacuzzi"
    SAFE = "safe"
    WORK_DESK = "work_desk"
    MOUNTAIN_VIEW = "mountain_view"
    CITY_VIEW = "city_view"


class UserRole(str, Enum):
    """Ролі користувачів у системі."""
    CLIENT = "client"            # Клієнт готелю
    ADMIN = "admin"              # Адміністратор системи / Менеджер
    STAFF = "staff"              # Обслуговуючий персонал


class LoyaltyTier(str, Enum):
    """
    Рівні програми лояльності клієнта.
    Визначають персональні знижки та відсоток нарахування кешбеку бонусами.
    """
    STANDARD = "standard"        # Знижка 0%, кешбек 3%
    SILVER = "silver"            # Знижка 5%, кешбек 5%
    GOLD = "gold"                # Знижка 10%, кешбек 7%
    PLATINUM = "platinum"        # Знижка 15%, кешбек 10%


class BookingStatus(str, Enum):
    """Статуси життєвого циклу бронювання."""
    CREATED = "created"          # Створено (очікує підтвердження або оплати)
    CONFIRMED = "confirmed"      # Підтверджено готелем
    CHECKED_IN = "checked_in"    # Гість заселився
    CHECKED_OUT = "checked_out"  # Гість виселився (бронювання успішно завершено)
    CANCELLED = "cancelled"      # Бронювання скасовано


class ServiceType(str, Enum):
    """Типи додаткових послуг готелю."""
    MEAL = "meal"                # Харчування (сніданок, вечеря, все включено)
    TRANSFER = "transfer"        # Трансфер (аеропорт/вокзал)
    SPA = "spa"                  # СПА-процедури, масаж, сауна
    CLEANING = "cleaning"        # Додаткове експрес-прибирання
    EXCURSION = "excursion"      # Екскурсійний супровід
