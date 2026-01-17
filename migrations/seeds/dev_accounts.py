"""
Development test accounts seed data.

Only seeded when DEV_MODE=true. Creates test users with various roles.
"""

import logging
import os
import sqlite3

from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() in ('true', '1', 'yes')


def seed_dev_accounts(conn: sqlite3.Connection) -> None:
    """Seed test accounts in DEV_MODE only."""
    if not DEV_MODE:
        return

    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count < 3:
        test_password = generate_password_hash('Test123!', method='pbkdf2:sha256')

        test_accounts = [
            ('auditor1@test.com', 'Alice Auditor', 'auditor'),
            ('auditor2@test.com', 'Bob Auditor', 'auditor'),
            ('reviewer1@test.com', 'Rachel Reviewer', 'reviewer'),
            ('reviewer2@test.com', 'Richard Reviewer', 'reviewer'),
            ('admin@test.com', 'Adam Admin', 'admin'),
            ('viewer1@test.com', 'Victor Viewer', 'viewer'),
        ]

        for email, name, role in test_accounts:
            # Check if user already exists
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not existing:
                is_admin = 1 if role == 'admin' else 0
                conn.execute("""
                    INSERT INTO users (email, name, password_hash, is_active, is_admin, role)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (email, name, test_password, is_admin, role))

        conn.commit()
        logger.info("DEV_MODE: Seeded test accounts")
