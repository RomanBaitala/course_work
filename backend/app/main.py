"""
Головна точка входу FastAPI додатку "Система управління готелем".
Підключає REST API маршрути, CORS middleware та автоматичну документацію Swagger.
"""

import os
import sys

# Додаємо бібліотеки та корінь бекенду в sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_DIR = os.path.join(BASE_DIR, "libs")
if LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin import router as admin_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.services import router as services_router
from app.api.v1.users import router as users_router
from app.database.connection import db_manager

# Ініціалізація додатку
app = FastAPI(
    title="Hotel Management System API",
    description="""
    REST API для курсової роботи «Система управління готелем» (Варіант №3).
    Включає управління номерним фондом, онлайн-бронювання, калькулятор вартості,
    персональний кабінет клієнта та аналітичні звіти для адміністрації.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Дозволяємо CORS для легкого підключення будь-якого фронтенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключення роутерів API v1
api_prefix = "/api/v1"
app.include_router(rooms_router, prefix=api_prefix)
app.include_router(services_router, prefix=api_prefix)
app.include_router(bookings_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)


@app.get("/", tags=["General"])
def root():
    """Кореневий ендпоінт перевірки працездатності сервера."""
    return JSONResponse(
        {
            "service": "Hotel Management System REST API",
            "status": "online",
            "version": "1.0.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "endpoints": {
                "rooms": f"{api_prefix}/rooms",
                "services": f"{api_prefix}/services",
                "bookings": f"{api_prefix}/bookings",
                "users": f"{api_prefix}/users",
                "admin_reports": f"{api_prefix}/admin/reports/financial",
            },
        }
    )
