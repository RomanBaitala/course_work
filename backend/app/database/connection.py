"""
Керування базою даних SQLite для системи управління готелем.
Створює таблиці, керує з'єднанням та транзакціями.
"""

from contextlib import contextmanager
import os
import sqlite3
from typing import Generator

# Шлях можна перевизначити змінною середовища HOTEL_DB_PATH (напр. для окремої тестової БД)
DEFAULT_DB_PATH = os.getenv(
    "HOTEL_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hotel.db")),
)


class DatabaseManager:
    """Клас для ініціалізації та взаємодії з базою даних SQLite."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Створює нове з'єднання з базою даних з увімкненими foreign keys."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Контекстний менеджер для безпечної роботи із транзакціями."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Створює схему таблиць у базі даних, якщо вони ще не існують."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'client',
            loyalty_tier TEXT NOT NULL DEFAULT 'standard',
            bonus_points REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            base_price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 2,
            description TEXT DEFAULT '',
            amenities TEXT DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'available',
            photo_urls TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS services (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            guest_id TEXT NOT NULL,
            room_id TEXT NOT NULL,
            check_in_date TEXT NOT NULL,
            check_out_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            total_price REAL NOT NULL,
            used_bonus_points REAL DEFAULT 0.0,
            earned_bonus_points REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (guest_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS booking_services (
            booking_id TEXT NOT NULL,
            service_id TEXT NOT NULL,
            price_at_booking REAL NOT NULL,
            PRIMARY KEY (booking_id, service_id),
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE RESTRICT
        );

        -- Індекси для швидкого пошуку та перевірки перетину дат
        CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);
        CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(room_type);
        CREATE INDEX IF NOT EXISTS idx_bookings_dates ON bookings(room_id, check_in_date, check_out_date);
        CREATE INDEX IF NOT EXISTS idx_bookings_guest ON bookings(guest_id);
        """
        with self.connection() as conn:
            conn.executescript(schema_sql)

    def clear_all(self) -> None:
        """Видаляє всі дані з таблиць (схема лишається). Порядок враховує зовнішні ключі."""
        with self.connection() as conn:
            for table in ("booking_services", "bookings", "services", "rooms", "users"):
                conn.execute(f"DELETE FROM {table};")


# Глобальний екземпляр менеджера бази даних
db_manager = DatabaseManager()
