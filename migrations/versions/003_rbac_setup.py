"""
003: RBAC setup.

Seeds default roles and creates default admin user if needed.
"""

import logging
import os
import secrets
import sqlite3

from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

# Import DEV_MODE from database module
DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() in ('true', '1', 'yes')


def upgrade(conn: sqlite3.Connection) -> None:
    """Setup RBAC roles and default admin."""

    # Seed roles if empty
    role_count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
    if role_count == 0:
        conn.executescript("""
            INSERT INTO roles (id, name, description, permissions) VALUES
                (1, 'admin', 'Full system access', '["*"]'),
                (2, 'auditor', 'Can edit assigned audits', '["audit.read", "audit.edit", "risk.read", "risk.edit", "issue.read", "issue.edit", "task.read", "task.edit"]'),
                (3, 'reviewer', 'Can read and add comments', '["audit.read", "risk.read", "issue.read", "task.read", "comment.create"]'),
                (4, 'viewer', 'Read-only access', '["audit.read", "risk.read", "issue.read", "task.read"]');
        """)
        conn.commit()

    # Bootstrap default admin if no users exist
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@localhost')
        admin_password = os.environ.get('ADMIN_PASSWORD')

        # Security: Never use hardcoded default password
        # Generate random password if not provided via environment
        generated_password = False
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
            generated_password = True

        password_hash = generate_password_hash(admin_password, method='pbkdf2:sha256')

        conn.execute("""
            INSERT INTO users (email, name, password_hash, is_active, is_admin)
            VALUES (?, 'Default Admin', ?, 1, 1)
        """, (admin_email, password_hash))
        conn.commit()

        # Log credentials - only show password in DEV_MODE
        if generated_password:
            if DEV_MODE:
                logger.warning(
                    "\n" + "="*60 + "\n"
                    "DEFAULT ADMIN CREATED WITH GENERATED PASSWORD\n"
                    "Email: %s\n"
                    "Password: %s\n"
                    "SAVE THIS PASSWORD - it will not be shown again!\n"
                    "Set ADMIN_EMAIL and ADMIN_PASSWORD env vars to customize.\n"
                    + "="*60,
                    admin_email, admin_password
                )
            else:
                logger.warning(
                    "Default admin created with generated password. "
                    "Check server startup logs or set ADMIN_EMAIL/ADMIN_PASSWORD env vars."
                )
