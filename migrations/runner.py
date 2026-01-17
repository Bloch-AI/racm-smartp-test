"""
Simple migration runner for SQLite databases.

Not Alembic - just a straightforward version-based migration system.
"""

import importlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Runs database migrations in order."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / 'versions'

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Create migrations tracking table if not exists."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def _get_current_version(self, conn: sqlite3.Connection) -> int:
        """Get the current schema version."""
        result = conn.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
        return result[0] or 0

    def _get_migration_modules(self) -> list:
        """Get all migration modules in order."""
        migrations = []
        for file in sorted(self.migrations_dir.glob('*.py')):
            if file.name.startswith('_'):
                continue
            # Parse version from filename (e.g., '001_initial_schema.py' -> 1)
            try:
                version = int(file.stem.split('_')[0])
                migrations.append((version, file.stem, file))
            except ValueError:
                logger.warning(f"Skipping invalid migration filename: {file.name}")
        return sorted(migrations, key=lambda x: x[0])

    def run_migrations(self) -> None:
        """Run all pending migrations."""
        conn = self._get_conn()
        try:
            self._ensure_migrations_table(conn)
            current_version = self._get_current_version(conn)

            migrations = self._get_migration_modules()
            pending = [(v, n, f) for v, n, f in migrations if v > current_version]

            if not pending:
                logger.debug("No pending migrations")
                return

            for version, name, filepath in pending:
                logger.info(f"Running migration {version}: {name}")
                try:
                    # Import and run the migration module
                    module = importlib.import_module(f'migrations.versions.{name}')
                    if hasattr(module, 'upgrade'):
                        module.upgrade(conn)
                    else:
                        logger.warning(f"Migration {name} has no upgrade() function")
                        continue

                    # Record the migration
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, name)
                    )
                    conn.commit()
                    logger.info(f"Migration {version} completed")

                except Exception as e:
                    conn.rollback()
                    logger.error(f"Migration {version} failed: {e}")
                    raise

        finally:
            conn.close()

    def get_status(self) -> dict:
        """Get migration status."""
        conn = self._get_conn()
        try:
            self._ensure_migrations_table(conn)
            current = self._get_current_version(conn)
            migrations = self._get_migration_modules()
            pending = [n for v, n, f in migrations if v > current]

            return {
                'current_version': current,
                'total_migrations': len(migrations),
                'pending_count': len(pending),
                'pending': pending
            }
        finally:
            conn.close()
