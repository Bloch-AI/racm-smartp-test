"""
005: Workflow columns.

Adds workflow state management columns to risks and issues.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Add workflow management columns."""

    # Add role column to users table
    try:
        conn.execute("SELECT role FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer'")
        # Migrate existing data: is_admin=1 becomes role='admin', others become 'auditor'
        conn.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
        conn.execute("UPDATE users SET role = 'auditor' WHERE is_admin = 0 AND role IS NULL")
        conn.commit()

    # Consolidate global 'reviewer' role into 'auditor'
    conn.execute("UPDATE users SET role = 'auditor' WHERE role = 'reviewer'")
    conn.commit()

    # Add auditor_id, reviewer_id, and created_by to audits table
    for col in ['auditor_id', 'reviewer_id', 'created_by']:
        try:
            conn.execute(f"SELECT {col} FROM audits LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE audits ADD COLUMN {col} INTEGER")
            conn.commit()

    # Create indexes for audit assignments
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_auditor ON audits(auditor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_reviewer ON audits(reviewer_id)")
    conn.commit()

    # Add workflow columns to risks table
    risk_workflow_columns = [
        ("record_status", "TEXT DEFAULT 'draft'"),
        ("current_owner_role", "TEXT DEFAULT 'auditor'"),
        ("admin_lock_reason", "TEXT"),
        ("admin_locked_by", "INTEGER"),
        ("admin_locked_at", "TIMESTAMP"),
        ("signed_off_by", "INTEGER"),
        ("signed_off_at", "TIMESTAMP"),
        ("created_by", "INTEGER"),
        ("updated_by", "INTEGER"),
    ]
    for col_name, col_type in risk_workflow_columns:
        try:
            conn.execute(f"SELECT {col_name} FROM risks LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE risks ADD COLUMN {col_name} {col_type}")
            conn.commit()

    # Add workflow columns to issues table
    issue_workflow_columns = [
        ("record_status", "TEXT DEFAULT 'draft'"),
        ("current_owner_role", "TEXT DEFAULT 'auditor'"),
        ("admin_lock_reason", "TEXT"),
        ("admin_locked_by", "INTEGER"),
        ("admin_locked_at", "TIMESTAMP"),
        ("signed_off_by", "INTEGER"),
        ("signed_off_at", "TIMESTAMP"),
        ("created_by", "INTEGER"),
        ("updated_by", "INTEGER"),
    ]
    for col_name, col_type in issue_workflow_columns:
        try:
            conn.execute(f"SELECT {col_name} FROM issues LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE issues ADD COLUMN {col_name} {col_type}")
            conn.commit()

    # Create indexes for record status
    conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_record_status ON risks(record_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_owner_role ON risks(current_owner_role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_record_status ON issues(record_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_owner_role ON issues(current_owner_role)")
    conn.commit()

    # Create record_state_history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS record_state_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            action TEXT NOT NULL,
            performed_by INTEGER REFERENCES users(id),
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            reason TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_record ON record_state_history(record_type, record_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_action ON record_state_history(action)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_user ON record_state_history(performed_by)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_date ON record_state_history(performed_at)")
    conn.commit()

    # Create audit_viewers table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_viewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            viewer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            granted_by INTEGER REFERENCES users(id),
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(audit_id, viewer_user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_viewers_audit ON audit_viewers(audit_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_viewers_user ON audit_viewers(viewer_user_id)")
    conn.commit()
