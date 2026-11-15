"""
Endpoints for Hotel Additional Services (meals, spa, transfer).
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import ServiceResponse
from app.repositories import ServiceRepository

router = APIRouter(prefix="/services", tags=["Additional Services"])
service_repo = ServiceRepository()


@router.get("", response_model=List[ServiceResponse], summary="Отримати список доступних платних послуг")
def get_services():
    services = service_repo.get_all()
    return [
        ServiceResponse(
            id=s.id,
            name=s.name,
            service_type=s.service_type.value,
            price=s.price,
            description=s.description,
        )
        for s in services
    ]


@router.get("/{service_id}", response_model=ServiceResponse, summary="Отримати послугу за ID")
def get_service_by_id(service_id: str):
    service = service_repo.get_by_id(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Послугу '{service_id}' не знайдено.")
    return ServiceResponse(
        id=service.id,
        name=service.name,
        service_type=service.service_type.value,
        price=service.price,
        description=service.description,
    )
