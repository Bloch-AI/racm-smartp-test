"""
006: Audit team table.

Creates the audit_team junction table and migrates existing assignments.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Create and populate audit_team table."""

    # Create audit_team junction table (replaces single auditor_id/reviewer_id)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            team_role TEXT NOT NULL CHECK (team_role IN ('auditor', 'reviewer')),
            assigned_by INTEGER REFERENCES users(id),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(audit_id, user_id, team_role)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_audit ON audit_team(audit_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_user ON audit_team(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_role ON audit_team(team_role)")
    conn.commit()

    # Migrate existing auditor_id/reviewer_id to audit_team
    existing_team = conn.execute("SELECT COUNT(*) FROM audit_team").fetchone()[0]
    if existing_team == 0:
        # Migrate existing auditor assignments
        conn.execute("""
            INSERT OR IGNORE INTO audit_team (audit_id, user_id, team_role)
            SELECT id, auditor_id, 'auditor' FROM audits
            WHERE auditor_id IS NOT NULL
        """)
        # Migrate existing reviewer assignments
        conn.execute("""
            INSERT OR IGNORE INTO audit_team (audit_id, user_id, team_role)
            SELECT id, reviewer_id, 'reviewer' FROM audits
            WHERE reviewer_id IS NOT NULL
        """)
        conn.commit()

    # Add assigned_reviewer_id to risks table
    try:
        conn.execute("SELECT assigned_reviewer_id FROM risks LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE risks ADD COLUMN assigned_reviewer_id INTEGER")
        conn.commit()

    # Add assigned_reviewer_id to issues table
    try:
        conn.execute("SELECT assigned_reviewer_id FROM issues LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE issues ADD COLUMN assigned_reviewer_id INTEGER")
        conn.commit()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_assigned_reviewer ON risks(assigned_reviewer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_assigned_reviewer ON issues(assigned_reviewer_id)")
    conn.commit()

    # Expand audit_team to allow 'viewer' role and migrate audit_viewers
    audit_team_schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='audit_team'"
    ).fetchone()
    if audit_team_schema and "'viewer'" not in audit_team_schema[0]:
        # Recreate audit_team with expanded CHECK constraint
        conn.execute("""
            CREATE TABLE audit_team_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                team_role TEXT NOT NULL CHECK (team_role IN ('auditor', 'reviewer', 'viewer')),
                assigned_by INTEGER REFERENCES users(id),
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                granted_by INTEGER REFERENCES users(id),
                granted_at TIMESTAMP,
                UNIQUE(audit_id, user_id, team_role)
            )
        """)
        # Copy existing audit_team data
        conn.execute("""
            INSERT INTO audit_team_new (id, audit_id, user_id, team_role, assigned_by, assigned_at)
            SELECT id, audit_id, user_id, team_role, assigned_by, assigned_at FROM audit_team
        """)
        conn.execute("DROP TABLE audit_team")
        conn.execute("ALTER TABLE audit_team_new RENAME TO audit_team")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_audit ON audit_team(audit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_user ON audit_team(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_team_role ON audit_team(team_role)")
        conn.commit()

    # Migrate audit_viewers data to audit_team (as 'viewer' role)
    viewers_exist = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_viewers'"
    ).fetchone()
    if viewers_exist:
        conn.execute("""
            INSERT OR IGNORE INTO audit_team (audit_id, user_id, team_role, granted_by, granted_at)
            SELECT audit_id, viewer_user_id, 'viewer', granted_by, granted_at
            FROM audit_viewers
        """)
        conn.commit()
