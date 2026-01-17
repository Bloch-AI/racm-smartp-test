"""
002: Add documentation columns to attachments tables.

Adds extracted_text and category columns if missing.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Add documentation-related columns."""

    # Migration: Add documentation column to issues if it doesn't exist
    try:
        conn.execute("SELECT documentation FROM issues LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE issues ADD COLUMN documentation TEXT DEFAULT ''")
        conn.commit()

    # Migration: Add category column to risk_attachments if it doesn't exist
    try:
        conn.execute("SELECT category FROM risk_attachments LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE risk_attachments ADD COLUMN category TEXT DEFAULT 'planning'")
        conn.commit()

    # Create category index after migration ensures column exists
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_category ON risk_attachments(category)")
    conn.commit()

    # Migration: Add extracted_text column to issue_attachments if it doesn't exist
    try:
        conn.execute("SELECT extracted_text FROM issue_attachments LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE issue_attachments ADD COLUMN extracted_text TEXT")
        conn.commit()

    # Migration: Add extracted_text column to risk_attachments if it doesn't exist
    try:
        conn.execute("SELECT extracted_text FROM risk_attachments LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE risk_attachments ADD COLUMN extracted_text TEXT")
        conn.commit()
