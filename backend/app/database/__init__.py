"""
Database package providing SQLite connection manager and initial seeds.
"""

from .connection import DatabaseManager, db_manager

__all__ = ["DatabaseManager", "db_manager"]
