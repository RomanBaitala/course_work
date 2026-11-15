"""
Репозиторій для роботи з користувачами готелю (UserRepository).
"""

from datetime import datetime
from typing import List, Optional

from app.database.connection import DatabaseManager, db_manager
from app.domain.models.entities import User
from app.domain.models.enums import LoyaltyTier, UserRole


class UserRepository:
    """Клас для збереження та отримання облікових записів гостей та персоналу."""

    def __init__(self, manager: DatabaseManager = db_manager):
        self.manager = manager

    def _row_to_entity(self, row) -> User:
        return User(
            id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            phone=row["phone"] or "",
            role=UserRole(row["role"]),
            loyalty_tier=LoyaltyTier(row["loyalty_tier"]),
            bonus_points=float(row["bonus_points"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def save(self, user: User) -> User:
        with self.manager.connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, full_name, email, phone, role, loyalty_tier, bonus_points, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    full_name = excluded.full_name,
                    email = excluded.email,
                    phone = excluded.phone,
                    role = excluded.role,
                    loyalty_tier = excluded.loyalty_tier,
                    bonus_points = excluded.bonus_points;
                """,
                (
                    user.id,
                    user.full_name,
                    user.email,
                    user.phone,
                    user.role.value,
                    user.loyalty_tier.value,
                    user.bonus_points,
                    user.created_at.isoformat(),
                ),
            )
        return user

    def update_bonus_points(self, user_id: str, new_balance: float) -> bool:
        with self.manager.connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET bonus_points = ? WHERE id = ?",
                (round(new_balance, 2), user_id),
            )
            return cursor.rowcount > 0

    def get_all(self) -> List[User]:
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM users ORDER BY created_at DESC;")
            return [self._row_to_entity(r) for r in cursor.fetchall()]
