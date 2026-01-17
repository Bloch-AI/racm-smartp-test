"""
Default roles seed data.

Seeds the required RBAC roles. This is called by migration 003.
"""

import sqlite3


def seed_roles(conn: sqlite3.Connection) -> None:
    """Seed default roles if table is empty."""
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
