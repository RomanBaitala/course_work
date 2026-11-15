"""
Репозиторій для роботи з додатковими послугами готелю (ServiceRepository).
"""

from typing import List, Optional

from app.database.connection import DatabaseManager, db_manager
from app.domain.models.entities import AdditionalService
from app.domain.models.enums import ServiceType


class ServiceRepository:
    """Клас для збереження та отримання переліку послуг готелю."""

    def __init__(self, manager: DatabaseManager = db_manager):
        self.manager = manager

    def _row_to_entity(self, row) -> AdditionalService:
        return AdditionalService(
            id=row["id"],
            name=row["name"],
            service_type=ServiceType(row["service_type"]),
            price=float(row["price"]),
            description=row["description"],
        )

    def get_by_id(self, service_id: str) -> Optional[AdditionalService]:
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_all(self) -> List[AdditionalService]:
        with self.manager.connection() as conn:
            cursor = conn.execute("SELECT * FROM services ORDER BY price ASC;")
            return [self._row_to_entity(r) for r in cursor.fetchall()]

    def save(self, service: AdditionalService) -> AdditionalService:
        with self.manager.connection() as conn:
            conn.execute(
                """
                INSERT INTO services (id, name, service_type, price, description)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    service_type = excluded.service_type,
                    price = excluded.price,
                    description = excluded.description;
                """,
                (
                    service.id,
                    service.name,
                    service.service_type.value,
                    service.price,
                    service.description,
                ),
            )
        return service
