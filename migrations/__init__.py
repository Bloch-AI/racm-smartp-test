"""
Database migrations module for RACM Smart-P.

Provides a simple migration system for SQLite database schema management.
"""

from .runner import MigrationRunner

__all__ = ['MigrationRunner']
