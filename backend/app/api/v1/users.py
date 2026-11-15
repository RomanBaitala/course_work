"""
Endpoints for User Accounts and Profiles.
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import UserResponse
from app.repositories import UserRepository

router = APIRouter(prefix="/users", tags=["Users & Profiles"])
user_repo = UserRepository()


def _user_to_response(u) -> UserResponse:
    return UserResponse(
        id=u.id,
        full_name=u.full_name,
        email=u.email,
        phone=u.phone,
        role=u.role.value,
        loyalty_tier=u.loyalty_tier.value,
        bonus_points=u.bonus_points,
        created_at=u.created_at,
    )


@router.get("", response_model=List[UserResponse], summary="Отримати список користувачів")
def get_users():
    return [_user_to_response(u) for u in user_repo.get_all()]


@router.get("/{user_id}", response_model=UserResponse, summary="Отримати профіль користувача")
def get_user_by_id(user_id: str):
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Користувача '{user_id}' не знайдено.")
    return _user_to_response(user)
