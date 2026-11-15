"""
Скрипт швидкого запуску веб-сервера Uvicorn для Hotel Management System.
Запуск: python backend/run_server.py
"""

import os
import sys

# Додаємо бібліотеки та корінь бекенду
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBS_DIR = os.path.join(BASE_DIR, "libs")
if LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🏨 Запуск сервера Hotel Management System...")
    print("🌐 API доступне за адресою:       http://127.0.0.1:8000")
    print("📄 Інтерактивна документація:    http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
