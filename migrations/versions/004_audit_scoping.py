"""
004: Audit scoping.

Adds audit_id columns to tables for multi-tenant audit support.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Add audit_id columns for scoping."""

    # Add audit_id column to tables that need scoping
    tables_needing_audit_id = [
        'risks', 'issues', 'tasks', 'flowcharts', 'test_documents',
        'risk_attachments', 'issue_attachments'
    ]
    for table in tables_needing_audit_id:
        try:
            conn.execute(f"SELECT audit_id FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN audit_id INTEGER")
            conn.commit()

    # Add risk_row_id to issues for proper FK
    try:
        conn.execute("SELECT risk_row_id FROM issues LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE issues ADD COLUMN risk_row_id INTEGER")
        conn.commit()

    # Get or create default audit for backfilling existing data
    existing_data = conn.execute("SELECT COUNT(*) FROM risks WHERE audit_id IS NULL").fetchone()[0]
    if existing_data > 0:
        # Check for existing default audit
        default_audit = conn.execute(
            "SELECT id FROM audits WHERE title = 'Default Audit (Migrated)'"
        ).fetchone()

        if default_audit:
            default_audit_id = default_audit[0]
        else:
            # Check if any audits exist
            first_audit = conn.execute("SELECT id FROM audits ORDER BY id LIMIT 1").fetchone()
            if first_audit:
                default_audit_id = first_audit[0]
            else:
                # Create new default audit
                cursor = conn.execute("""
                    INSERT INTO audits (title, description, status)
                    VALUES ('Default Audit (Migrated)',
                            'Auto-created during migration to hold existing data',
                            'in_progress')
                """)
                conn.commit()
                default_audit_id = cursor.lastrowid

        # Backfill audit_id for all tables with NULL values
        for table in tables_needing_audit_id:
            conn.execute(f"UPDATE {table} SET audit_id = ? WHERE audit_id IS NULL", (default_audit_id,))
        conn.commit()

        # Backfill issues.risk_row_id from TEXT risk_id
        conn.execute("""
            UPDATE issues
            SET risk_row_id = (
                SELECT risks.id FROM risks
                WHERE risks.risk_id = issues.risk_id
                AND risks.audit_id = issues.audit_id
            )
            WHERE risk_row_id IS NULL AND risk_id IS NOT NULL
        """)
        conn.commit()

    # Create indexes for audit_id columns
    for table in tables_needing_audit_id:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_audit ON {table}(audit_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_risk_row ON issues(risk_row_id)")
    conn.commit()

    # Fix flowcharts uniqueness - change from global name to (audit_id, name)
    flowchart_schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='flowcharts'"
    ).fetchone()
    if flowchart_schema and 'name TEXT UNIQUE' in flowchart_schema[0]:
        # Recreate table with correct uniqueness constraint
        conn.execute("""
            CREATE TABLE flowcharts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data JSON NOT NULL,
                risk_id INTEGER REFERENCES risks(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                audit_id INTEGER,
                UNIQUE(audit_id, name)
            )
        """)
        conn.execute("""
            INSERT INTO flowcharts_new (id, name, data, risk_id, created_at, updated_at, audit_id)
            SELECT id, name, data, risk_id, created_at, updated_at, audit_id FROM flowcharts
        """)
        conn.execute("DROP TABLE flowcharts")
        conn.execute("ALTER TABLE flowcharts_new RENAME TO flowcharts")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flowcharts_risk ON flowcharts(risk_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flowcharts_audit ON flowcharts(audit_id)")
        conn.commit()
