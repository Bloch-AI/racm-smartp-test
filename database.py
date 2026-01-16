"""
RACM Audit Toolkit - SQLite Database Module

Provides persistent storage for:
- Risks/Controls (RACM spreadsheet)
- Tasks (Kanban board)
- Flowcharts (Drawflow diagrams)

Can be imported as a module into larger projects.
"""

import sqlite3
import json
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Default database path - can be overridden
DEFAULT_DB_PATH = Path(__file__).parent / "racm_data.db"


class RACMDatabase:
    """SQLite database for RACM audit data with AI-queryable structure."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dicts instead of tuples
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _connection(self):
        """Context manager for database connections."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            -- Risks and Controls (RACM rows)
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_id TEXT UNIQUE NOT NULL,
                risk TEXT,
                control_id TEXT,
                control_owner TEXT,
                design_effectiveness_testing TEXT,
                design_effectiveness_conclusion TEXT,
                operational_effectiveness_test TEXT,
                operational_effectiveness_conclusion TEXT,
                status TEXT DEFAULT 'Not Complete',
                ready_for_review INTEGER DEFAULT 0,
                reviewer TEXT,
                raise_issue INTEGER DEFAULT 0,
                closed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Kanban Tasks (for individual audit execution)
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                assignee TEXT,
                column_id TEXT DEFAULT 'planning',
                risk_id INTEGER REFERENCES risks(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Annual Audit Plan (list of all audits planned for the year)
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                audit_area TEXT,
                owner TEXT,
                planned_start DATE,
                planned_end DATE,
                actual_start DATE,
                actual_end DATE,
                quarter TEXT,
                status TEXT DEFAULT 'planning',
                priority TEXT DEFAULT 'medium',
                estimated_hours REAL,
                actual_hours REAL,
                risk_rating TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Flowcharts (stores Drawflow JSON)
            CREATE TABLE IF NOT EXISTS flowcharts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                data JSON NOT NULL,
                risk_id INTEGER REFERENCES risks(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Test Documents (stores Quill rich text for DE/OE Testing)
            CREATE TABLE IF NOT EXISTS test_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_id INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
                doc_type TEXT NOT NULL CHECK (doc_type IN ('de_testing', 'oe_testing')),
                content TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(risk_id, doc_type)
            );

            -- Issues (Issue Log linked to RACM)
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT UNIQUE NOT NULL,
                risk_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Open',
                assigned_to TEXT,
                due_date DATE,
                documentation TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Index for common queries
            CREATE INDEX IF NOT EXISTS idx_risks_status ON risks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_risk ON tasks(risk_id);
            CREATE INDEX IF NOT EXISTS idx_flowcharts_risk ON flowcharts(risk_id);
            CREATE INDEX IF NOT EXISTS idx_test_docs_risk ON test_documents(risk_id);
            CREATE INDEX IF NOT EXISTS idx_issues_risk ON issues(risk_id);
            CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
            CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);
            CREATE INDEX IF NOT EXISTS idx_audits_quarter ON audits(quarter);

            -- Issue Attachments (file evidence)
            CREATE TABLE IF NOT EXISTS issue_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                description TEXT,
                extracted_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_attachments_issue ON issue_attachments(issue_id);

            -- Risk Attachments (file evidence for RACM)
            CREATE TABLE IF NOT EXISTS risk_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_id TEXT NOT NULL,
                category TEXT DEFAULT 'planning',
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                description TEXT,
                extracted_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_attachments_risk ON risk_attachments(risk_id);

            -- Audit Attachments (file evidence for annual audit plan)
            CREATE TABLE IF NOT EXISTS audit_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                description TEXT,
                extracted_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_attachments_audit ON audit_attachments(audit_id);

            -- Audit Library Documents (reference materials like COBIT, COSO, IIA Standards)
            CREATE TABLE IF NOT EXISTS library_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                doc_type TEXT DEFAULT 'framework',
                source TEXT,
                description TEXT,
                file_size INTEGER,
                mime_type TEXT,
                total_chunks INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Library Document Chunks (for RAG retrieval)
            CREATE TABLE IF NOT EXISTS library_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES library_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                section TEXT,
                content TEXT NOT NULL,
                token_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_library_chunks_doc ON library_chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_library_docs_type ON library_documents(doc_type);
            CREATE INDEX IF NOT EXISTS idx_library_docs_source ON library_documents(source);

            -- Users (authentication)
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

            -- Roles (for RBAC)
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                permissions TEXT
            );

            -- Audit Memberships (users assigned to audits with roles)
            CREATE TABLE IF NOT EXISTS audit_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(audit_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_memberships_audit ON audit_memberships(audit_id);
            CREATE INDEX IF NOT EXISTS idx_memberships_user ON audit_memberships(user_id);

            -- Felix AI Conversations
            CREATE TABLE IF NOT EXISTS felix_conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                title TEXT DEFAULT 'New Chat',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_felix_conversations_user ON felix_conversations(user_id);

            -- Felix AI Messages
            CREATE TABLE IF NOT EXISTS felix_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES felix_conversations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_felix_messages_conv ON felix_messages(conversation_id);

            -- Felix AI Attachments
            CREATE TABLE IF NOT EXISTS felix_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                mime_type TEXT,
                extracted_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES felix_conversations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_felix_attachments_conv ON felix_attachments(conversation_id);
        """)
        conn.commit()

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

        # ==================== RBAC MIGRATIONS ====================

        # Migration: Seed roles if empty
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

        # Migration: Bootstrap default admin if no users exist
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            import os
            from werkzeug.security import generate_password_hash
            import logging

            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@localhost')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123')
            password_hash = generate_password_hash(admin_password, method='pbkdf2:sha256')

            conn.execute("""
                INSERT INTO users (email, name, password_hash, is_active, is_admin)
                VALUES (?, 'Default Admin', ?, 1, 1)
            """, (admin_email, password_hash))
            conn.commit()

            # Log warning about default credentials
            if admin_password == 'changeme123':
                logging.warning(
                    "Default admin created with email '%s' and default password. "
                    "Please change the password immediately! "
                    "Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables for custom credentials.",
                    admin_email
                )

        # Migration: Add audit_id column to tables that need scoping
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

        # Migration: Add risk_row_id to issues for proper FK
        try:
            conn.execute("SELECT risk_row_id FROM issues LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE issues ADD COLUMN risk_row_id INTEGER")
            conn.commit()

        # Migration: Get or create default audit for backfilling existing data
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

        # ==================== WORKFLOW STATE MIGRATIONS ====================

        # Migration: Add role column to users table
        try:
            conn.execute("SELECT role FROM users LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer'")
            # Migrate existing data: is_admin=1 becomes role='admin', others become 'auditor'
            conn.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
            conn.execute("UPDATE users SET role = 'auditor' WHERE is_admin = 0 AND role IS NULL")
            conn.commit()

        # Migration: Add auditor_id and reviewer_id to audits table
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

        # Migration: Add workflow columns to risks table
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

        # Migration: Add workflow columns to issues table
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

        # Migration: Create record_state_history table
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

        # Migration: Create audit_viewers table
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

        # ==================== AUDIT TEAM MIGRATIONS ====================

        # Migration: Create audit_team junction table (replaces single auditor_id/reviewer_id)
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

        # Migration: Migrate existing auditor_id/reviewer_id to audit_team
        # Check if migration has already been done
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

        # Migration: Add assigned_reviewer_id to risks table (for tracking which reviewer was selected)
        try:
            conn.execute("SELECT assigned_reviewer_id FROM risks LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE risks ADD COLUMN assigned_reviewer_id INTEGER")
            conn.commit()

        # Migration: Add assigned_reviewer_id to issues table
        try:
            conn.execute("SELECT assigned_reviewer_id FROM issues LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE issues ADD COLUMN assigned_reviewer_id INTEGER")
            conn.commit()

        conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_assigned_reviewer ON risks(assigned_reviewer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_assigned_reviewer ON issues(assigned_reviewer_id)")
        conn.commit()

        # ==================== SEED TEST ACCOUNTS ====================
        # Only seed if we have less than 3 users (just the default admin)
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count < 3:
            from werkzeug.security import generate_password_hash
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

        conn.close()

    # ==================== RISKS (RACM) ====================

    def get_all_risks(self) -> List[Dict]:
        """Get all risks/controls."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM risks ORDER BY risk_id").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_risk(self, risk_id: str) -> Optional[Dict]:
        """Get a single risk by risk_id (e.g., 'R001')."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM risks WHERE risk_id = ?", (risk_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_risk_by_id(self, id: int) -> Optional[Dict]:
        """Get a single risk by database ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM risks WHERE id = ?", (id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_risk(self, risk_id: str, risk: str = "", control_id: str = "",
                    control_owner: str = "", design_effectiveness_testing: str = "",
                    design_effectiveness_conclusion: str = "", operational_effectiveness_test: str = "",
                    operational_effectiveness_conclusion: str = "", status: str = "Not Complete",
                    ready_for_review: int = 0, reviewer: str = "",
                    raise_issue: int = 0, closed: int = 0) -> int:
        """Create a new risk/control. Returns the new ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO risks (risk_id, risk, control_id, control_owner, design_effectiveness_testing,
                              design_effectiveness_conclusion, operational_effectiveness_test,
                              operational_effectiveness_conclusion, status, ready_for_review,
                              reviewer, raise_issue, closed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (risk_id, risk, control_id, control_owner, design_effectiveness_testing,
              design_effectiveness_conclusion, operational_effectiveness_test,
              operational_effectiveness_conclusion, status, ready_for_review,
              reviewer, raise_issue, closed))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_risk(self, risk_id: str, **kwargs) -> bool:
        """Update a risk. Pass fields to update as kwargs."""
        allowed = {'risk', 'control_id', 'control_owner', 'design_effectiveness_testing',
                   'design_effectiveness_conclusion', 'operational_effectiveness_test',
                   'operational_effectiveness_conclusion', 'status', 'ready_for_review',
                   'reviewer', 'raise_issue', 'closed'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())

        conn = self._get_conn()
        conn.execute(f"UPDATE risks SET {set_clause} WHERE risk_id = ?",
                    (*updates.values(), risk_id))
        conn.commit()
        conn.close()
        return True

    def delete_risk(self, risk_id: str) -> bool:
        """Delete a risk by risk_id."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM risks WHERE risk_id = ?", (risk_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_risks_by_status(self, status: str) -> List[Dict]:
        """Get all risks with a specific status."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM risks WHERE status = ?", (status,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_risk_summary(self) -> Dict:
        """Get summary statistics for risks."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM risks").fetchone()[0]
        by_status = conn.execute("""
            SELECT status, COUNT(*) as count FROM risks GROUP BY status
        """).fetchall()
        conn.close()
        return {
            'total': total,
            'by_status': {row['status']: row['count'] for row in by_status}
        }

    # ==================== TASKS (KANBAN) ====================

    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            ORDER BY t.created_at
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_tasks_by_column(self, column_id: str) -> List[Dict]:
        """Get tasks in a specific column."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            WHERE t.column_id = ?
            ORDER BY t.created_at
        """, (column_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_task(self, task_id: int) -> Optional[Dict]:
        """Get a single task by ID."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            WHERE t.id = ?
        """, (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_task(self, title: str, description: str = "", priority: str = "medium",
                    assignee: str = "", column_id: str = "planning",
                    risk_id: Optional[str] = None) -> int:
        """Create a new task. risk_id can be the string ID (e.g., 'R001')."""
        conn = self._get_conn()

        # Look up risk foreign key if provided
        fk_risk_id = None
        if risk_id:
            row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (risk_id,)).fetchone()
            if row:
                fk_risk_id = row['id']

        cursor = conn.execute("""
            INSERT INTO tasks (title, description, priority, assignee, column_id, risk_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, priority, assignee, column_id, fk_risk_id))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Update a task. Pass fields to update as kwargs."""
        allowed = {'title', 'description', 'priority', 'assignee', 'column_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())

        conn = self._get_conn()
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?",
                    (*updates.values(), task_id))
        conn.commit()
        conn.close()
        return True

    def move_task(self, task_id: int, column_id: str) -> bool:
        """Move a task to a different column."""
        return self.update_task(task_id, column_id=column_id)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_task_summary(self) -> Dict:
        """Get summary statistics for tasks."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        by_column = conn.execute("""
            SELECT column_id, COUNT(*) as count FROM tasks GROUP BY column_id
        """).fetchall()
        by_priority = conn.execute("""
            SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority
        """).fetchall()
        conn.close()
        return {
            'total': total,
            'by_column': {row['column_id']: row['count'] for row in by_column},
            'by_priority': {row['priority']: row['count'] for row in by_priority}
        }

    # ==================== AUDITS (Annual Audit Plan) ====================

    def get_all_audits(self) -> List[Dict]:
        """Get all audits from the annual audit plan."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM audits ORDER BY
                CASE quarter
                    WHEN 'Q1' THEN 1
                    WHEN 'Q2' THEN 2
                    WHEN 'Q3' THEN 3
                    WHEN 'Q4' THEN 4
                    ELSE 5
                END,
                planned_start,
                title
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audit(self, audit_id: int) -> Optional[Dict]:
        """Get a single audit by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_audit(self, title: str, **kwargs) -> int:
        """Create a new audit in the annual plan."""
        conn = self._get_conn()
        allowed = {'description', 'audit_area', 'owner', 'planned_start', 'planned_end',
                   'actual_start', 'actual_end', 'quarter', 'status', 'priority',
                   'estimated_hours', 'actual_hours', 'risk_rating', 'notes'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed}

        columns = ['title'] + list(filtered.keys())
        placeholders = ['?'] * len(columns)
        values = [title] + list(filtered.values())

        cursor = conn.execute(
            f"INSERT INTO audits ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
            values
        )
        conn.commit()
        audit_id = cursor.lastrowid
        conn.close()
        return audit_id

    def update_audit(self, audit_id: int, **kwargs) -> bool:
        """Update an audit. Pass fields to update as kwargs."""
        allowed = {'title', 'description', 'audit_area', 'owner', 'planned_start',
                   'planned_end', 'actual_start', 'actual_end', 'quarter', 'status',
                   'priority', 'estimated_hours', 'actual_hours', 'risk_rating', 'notes'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        updates['updated_at'] = 'CURRENT_TIMESTAMP'

        conn = self._get_conn()
        set_clause = ', '.join(f"{k} = ?" if k != 'updated_at' else f"{k} = CURRENT_TIMESTAMP"
                               for k in updates.keys())
        values = [v for k, v in updates.items() if k != 'updated_at']
        conn.execute(f"UPDATE audits SET {set_clause} WHERE id = ?", (*values, audit_id))
        conn.commit()
        conn.close()
        return True

    def delete_audit(self, audit_id: int) -> bool:
        """Delete an audit from the annual plan."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM audits WHERE id = ?", (audit_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def audits_to_spreadsheet_format(self, audits: List[Dict]) -> List[List]:
        """Convert audit dicts to spreadsheet format (array of arrays)."""
        return [
            [
                str(a['id']),
                a['title'] or '',
                a['audit_area'] or '',
                a['owner'] or '',
                a['planned_start'] or '',
                a['planned_end'] or '',
                a['quarter'] or '',
                a['status'] or 'planning',
                a['priority'] or 'medium',
                a['risk_rating'] or '',
                str(a['estimated_hours']) if a['estimated_hours'] else '',
                a['description'] or ''
            ]
            for a in audits
        ]

    def get_audits_as_spreadsheet(self) -> List[List]:
        """Get all audits in spreadsheet format (array of arrays)."""
        audits = self.get_all_audits()
        return self.audits_to_spreadsheet_format(audits)

    def save_audits_from_spreadsheet(self, data: List[List]) -> Dict:
        """Save audits from spreadsheet format. Returns stats."""
        conn = self._get_conn()
        existing_ids = {row['id'] for row in conn.execute("SELECT id FROM audits").fetchall()}
        seen_ids = set()
        created = 0
        updated = 0

        for row in data:
            if not row or len(row) < 2:
                continue

            # Parse row data
            audit_id = int(row[0]) if row[0] and str(row[0]).isdigit() else None
            title = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            if not title:
                continue

            audit_data = {
                'title': title,
                'audit_area': str(row[2]).strip() if len(row) > 2 and row[2] else None,
                'owner': str(row[3]).strip() if len(row) > 3 and row[3] else None,
                'planned_start': str(row[4]).strip() if len(row) > 4 and row[4] else None,
                'planned_end': str(row[5]).strip() if len(row) > 5 and row[5] else None,
                'quarter': str(row[6]).strip() if len(row) > 6 and row[6] else None,
                'status': str(row[7]).strip() if len(row) > 7 and row[7] else 'planning',
                'priority': str(row[8]).strip() if len(row) > 8 and row[8] else 'medium',
                'risk_rating': str(row[9]).strip() if len(row) > 9 and row[9] else None,
                'estimated_hours': float(row[10]) if len(row) > 10 and row[10] else None,
                'description': str(row[11]).strip() if len(row) > 11 and row[11] else None
            }

            if audit_id and audit_id in existing_ids:
                self.update_audit(audit_id, **audit_data)
                seen_ids.add(audit_id)
                updated += 1
            else:
                new_id = self.create_audit(**audit_data)
                seen_ids.add(new_id)
                created += 1

        # Delete audits that were removed from spreadsheet
        deleted = 0
        for audit_id in existing_ids - seen_ids:
            self.delete_audit(audit_id)
            deleted += 1

        conn.close()
        return {'created': created, 'updated': updated, 'deleted': deleted}

    def audits_to_kanban_format(self, audits: List[Dict]) -> Dict:
        """Convert audit dicts to kanban board format."""
        columns = ['planning', 'in_progress', 'fieldwork', 'review', 'complete']
        column_titles = {
            'planning': 'Planning',
            'in_progress': 'In Progress',
            'fieldwork': 'Fieldwork',
            'review': 'Review',
            'complete': 'Complete'
        }

        board = {
            'name': 'Annual Audit Plan',
            'columns': []
        }

        for col_id in columns:
            col_audits = [a for a in audits if (a['status'] or 'planning') == col_id]
            board['columns'].append({
                'id': col_id,
                'title': column_titles.get(col_id, col_id.title()),
                'items': [
                    {
                        'id': str(a['id']),
                        'title': a['title'],
                        'description': a['description'] or '',
                        'priority': a['priority'] or 'medium',
                        'owner': a['owner'] or '',
                        'quarter': a['quarter'] or '',
                        'audit_area': a['audit_area'] or '',
                        'planned_start': a['planned_start'] or '',
                        'planned_end': a['planned_end'] or ''
                    }
                    for a in col_audits
                ]
            })

        return board

    def get_audits_as_kanban(self) -> Dict:
        """Get all audits grouped by status for kanban view."""
        audits = self.get_all_audits()
        return self.audits_to_kanban_format(audits)

    def get_audit_summary(self) -> Dict:
        """Get summary statistics for annual audit plan."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM audits").fetchone()[0]
        by_status = conn.execute("""
            SELECT status, COUNT(*) as count FROM audits GROUP BY status
        """).fetchall()
        by_quarter = conn.execute("""
            SELECT quarter, COUNT(*) as count FROM audits GROUP BY quarter
        """).fetchall()
        by_area = conn.execute("""
            SELECT audit_area, COUNT(*) as count FROM audits GROUP BY audit_area
        """).fetchall()
        conn.close()
        return {
            'total': total,
            'by_status': {row['status'] or 'planning': row['count'] for row in by_status},
            'by_quarter': {row['quarter']: row['count'] for row in by_quarter if row['quarter']},
            'by_area': {row['audit_area']: row['count'] for row in by_area if row['audit_area']}
        }

    # ==================== FLOWCHARTS ====================

    def get_all_flowcharts(self) -> List[Dict]:
        """Get all flowcharts (metadata only, not full data)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, name, risk_id, created_at, updated_at
            FROM flowcharts ORDER BY name
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_flowchart(self, name: str) -> Optional[Dict]:
        """Get a flowchart by name (includes full Drawflow data)."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM flowcharts WHERE name = ?", (name,)).fetchone()
        conn.close()
        if row:
            result = dict(row)
            result['data'] = json.loads(result['data'])
            return result
        return None

    def save_flowchart(self, name: str, data: Dict, risk_id: Optional[str] = None, audit_id: Optional[int] = None) -> int:
        """Save/update a flowchart. Returns the ID."""
        conn = self._get_conn()

        # Look up risk foreign key if provided
        fk_risk_id = None
        if risk_id:
            row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (risk_id,)).fetchone()
            if row:
                fk_risk_id = row['id']

        # Upsert
        cursor = conn.execute("""
            INSERT INTO flowcharts (name, data, risk_id, audit_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                data = excluded.data,
                risk_id = excluded.risk_id,
                audit_id = excluded.audit_id,
                updated_at = CURRENT_TIMESTAMP
        """, (name, json.dumps(data), fk_risk_id, audit_id))
        conn.commit()

        # Get the ID
        row = conn.execute("SELECT id FROM flowcharts WHERE name = ?", (name,)).fetchone()
        flowchart_id = row['id'] if row else cursor.lastrowid
        conn.close()
        return flowchart_id

    def delete_flowchart(self, name: str) -> bool:
        """Delete a flowchart by name."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM flowcharts WHERE name = ?", (name,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ==================== TEST DOCUMENTS ====================

    def get_test_document(self, risk_id: int, doc_type: str) -> Optional[Dict]:
        """Get a test document by risk ID and type (de_testing or oe_testing)."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM test_documents WHERE risk_id = ? AND doc_type = ?",
            (risk_id, doc_type)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_test_document_by_risk_code(self, risk_code: str, doc_type: str) -> Optional[Dict]:
        """Get a test document by risk code (e.g., 'R001') and type."""
        conn = self._get_conn()
        # First get the risk ID
        risk_row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (risk_code,)).fetchone()
        if not risk_row:
            conn.close()
            return None
        risk_id = risk_row['id']
        row = conn.execute(
            "SELECT * FROM test_documents WHERE risk_id = ? AND doc_type = ?",
            (risk_id, doc_type)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def save_test_document(self, risk_id: int, doc_type: str, content: str) -> int:
        """Save/update a test document. Returns the ID."""
        conn = self._get_conn()
        # Get audit_id from the associated risk
        risk_row = conn.execute("SELECT audit_id FROM risks WHERE id = ?", (risk_id,)).fetchone()
        audit_id = risk_row['audit_id'] if risk_row else None
        cursor = conn.execute("""
            INSERT INTO test_documents (risk_id, doc_type, content, audit_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(risk_id, doc_type) DO UPDATE SET
                content = excluded.content,
                audit_id = excluded.audit_id,
                updated_at = CURRENT_TIMESTAMP
        """, (risk_id, doc_type, content, audit_id))
        conn.commit()
        row = conn.execute(
            "SELECT id FROM test_documents WHERE risk_id = ? AND doc_type = ?",
            (risk_id, doc_type)
        ).fetchone()
        doc_id = row['id'] if row else cursor.lastrowid
        conn.close()
        return doc_id

    def save_test_document_by_risk_code(self, risk_code: str, doc_type: str, content: str) -> Optional[int]:
        """Save/update a test document by risk code. Returns the ID or None if risk not found."""
        conn = self._get_conn()
        risk_row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (risk_code,)).fetchone()
        conn.close()
        if not risk_row:
            return None
        return self.save_test_document(risk_row['id'], doc_type, content)

    def delete_test_document(self, risk_id: int, doc_type: str) -> bool:
        """Delete a test document."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM test_documents WHERE risk_id = ? AND doc_type = ?",
            (risk_id, doc_type)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_test_documents_for_risk(self, risk_id: int) -> Dict[str, str]:
        """Get all test documents for a risk. Returns dict with doc_type as key."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT doc_type, content FROM test_documents WHERE risk_id = ?",
            (risk_id,)
        ).fetchall()
        conn.close()
        return {row['doc_type']: row['content'] for row in rows}

    def has_test_document(self, risk_code: str, doc_type: str) -> bool:
        """Check if a test document exists for a risk."""
        doc = self.get_test_document_by_risk_code(risk_code, doc_type)
        return doc is not None and bool(doc.get('content', '').strip())

    def get_all_test_documents_metadata(self) -> List[Dict]:
        """Get metadata about all test documents (without full content).
        Returns list of {risk_code, doc_type, has_content, word_count, updated_at}."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT r.risk_id as risk_code, td.doc_type, td.content, td.updated_at
            FROM test_documents td
            JOIN risks r ON td.risk_id = r.id
            ORDER BY r.risk_id, td.doc_type
        """).fetchall()
        conn.close()

        result = []
        for row in rows:
            content = row['content'] or ''
            # Strip HTML tags for word count approximation
            text_only = re.sub(r'<[^>]+>', '', content)
            word_count = len(text_only.split()) if text_only.strip() else 0
            result.append({
                'risk_code': row['risk_code'],
                'doc_type': row['doc_type'],
                'has_content': bool(content.strip()),
                'word_count': word_count,
                'updated_at': row['updated_at']
            })
        return result

    def get_flowchart_with_details(self, name: str) -> Optional[Dict]:
        """Get flowchart with parsed node details for AI consumption."""
        fc = self.get_flowchart(name)
        if not fc:
            return None

        # Extract node details from Drawflow data
        data = fc.get('data', {})
        nodes = []
        try:
            drawflow_data = data.get('drawflow', {}).get('Home', {}).get('data', {})
            for node_id, node in drawflow_data.items():
                nodes.append({
                    'id': node_id,
                    'type': node.get('name', 'unknown'),
                    'label': node.get('data', {}).get('name', ''),
                    'description': node.get('data', {}).get('description', '')
                })
        except (AttributeError, KeyError):
            pass

        return {
            'name': fc['name'],
            'risk_id': fc.get('risk_id'),
            'nodes': nodes,
            'updated_at': fc.get('updated_at')
        }

    # ==================== ISSUES (Issue Log) ====================

    def _generate_issue_id(self) -> str:
        """Generate next issue ID (ISS-001, ISS-002, etc.)."""
        conn = self._get_conn()
        row = conn.execute("SELECT MAX(CAST(SUBSTR(issue_id, 5) AS INTEGER)) as max_num FROM issues").fetchone()
        conn.close()
        next_num = (row['max_num'] or 0) + 1
        return f"ISS-{next_num:03d}"

    def create_issue(self, risk_id: str, title: str, description: str = '',
                     severity: str = 'Medium', status: str = 'Open',
                     assigned_to: str = '', due_date: str = None,
                     documentation: str = '') -> str:
        """Create a new issue. Returns the issue_id."""
        issue_id = self._generate_issue_id()
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO issues (issue_id, risk_id, title, description, severity, status, assigned_to, due_date, documentation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (issue_id, risk_id.upper(), title, description, severity, status, assigned_to, due_date, documentation))
        conn.commit()
        conn.close()
        return issue_id

    def get_all_issues(self) -> List[Dict]:
        """Get all issues."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM issues ORDER BY issue_id").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_issue(self, issue_id: str) -> Optional[Dict]:
        """Get a single issue by issue_id."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id.upper(),)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_issues_for_risk(self, risk_id: str) -> List[Dict]:
        """Get all issues for a specific risk."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM issues WHERE risk_id = ? ORDER BY issue_id", (risk_id.upper(),)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_issue(self, issue_id: str, **kwargs) -> bool:
        """Update an issue. Returns True if found and updated."""
        allowed_fields = ['title', 'description', 'severity', 'status', 'assigned_to', 'due_date', 'risk_id', 'documentation']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not updates:
            return False

        conn = self._get_conn()
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [issue_id.upper()]
        cursor = conn.execute(f"UPDATE issues SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE issue_id = ?", values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue. Returns True if found and deleted."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM issues WHERE issue_id = ?", (issue_id.upper(),))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_issues_as_spreadsheet(self) -> List[List]:
        """Get issues in spreadsheet format for jspreadsheet."""
        issues = self.get_all_issues()
        return [
            [
                issue['issue_id'],
                issue['risk_id'],
                issue['title'],
                issue['description'] or '',
                issue['severity'],
                issue['status'],
                issue['assigned_to'] or '',
                issue['due_date'] or ''
            ]
            for issue in issues
        ]

    def save_issues_from_spreadsheet(self, data: List[List]):
        """Save issues from spreadsheet format."""
        conn = self._get_conn()

        # Get existing issue IDs
        existing = {row['issue_id'] for row in conn.execute("SELECT issue_id FROM issues").fetchall()}
        seen = set()

        for row in data:
            if not row or len(row) < 3:
                continue

            issue_id = str(row[0]).strip().upper() if row[0] else ''
            risk_id = str(row[1]).strip().upper() if row[1] else ''
            title = str(row[2]).strip() if row[2] else ''

            if not title:  # Skip empty rows
                continue

            description = str(row[3]).strip() if len(row) > 3 and row[3] else ''
            severity = str(row[4]).strip() if len(row) > 4 and row[4] else 'Medium'
            status = str(row[5]).strip() if len(row) > 5 and row[5] else 'Open'
            assigned_to = str(row[6]).strip() if len(row) > 6 and row[6] else ''
            due_date = str(row[7]).strip() if len(row) > 7 and row[7] else None

            if issue_id and issue_id in existing:
                # Update existing
                conn.execute("""
                    UPDATE issues SET risk_id=?, title=?, description=?, severity=?, status=?,
                    assigned_to=?, due_date=?, updated_at=CURRENT_TIMESTAMP
                    WHERE issue_id=?
                """, (risk_id, title, description, severity, status, assigned_to, due_date, issue_id))
                seen.add(issue_id)
            else:
                # Create new
                new_id = self._generate_issue_id()
                conn.execute("""
                    INSERT INTO issues (issue_id, risk_id, title, description, severity, status, assigned_to, due_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_id, risk_id, title, description, severity, status, assigned_to, due_date))
                seen.add(new_id)

        # Delete removed issues (those in existing but not in seen)
        for issue_id in existing - seen:
            conn.execute("DELETE FROM issues WHERE issue_id = ?", (issue_id,))

        conn.commit()
        conn.close()

    def get_issue_documentation(self, issue_id: str) -> Optional[str]:
        """Get documentation for an issue."""
        conn = self._get_conn()
        row = conn.execute("SELECT documentation FROM issues WHERE issue_id = ?", (issue_id.upper(),)).fetchone()
        conn.close()
        return row['documentation'] if row else None

    def save_issue_documentation(self, issue_id: str, documentation: str) -> bool:
        """Save documentation for an issue."""
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE issues SET documentation = ?, updated_at = CURRENT_TIMESTAMP WHERE issue_id = ?",
            (documentation, issue_id.upper())
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def has_issue_documentation(self, issue_id: str) -> bool:
        """Check if an issue has documentation."""
        doc = self.get_issue_documentation(issue_id)
        return doc is not None and bool(doc.strip())

    def get_issue_summary(self) -> Dict:
        """Get summary of issues by status."""
        conn = self._get_conn()
        rows = conn.execute("SELECT status, COUNT(*) as count FROM issues GROUP BY status").fetchall()
        total = conn.execute("SELECT COUNT(*) as total FROM issues").fetchone()['total']
        conn.close()
        return {
            'total': total,
            'by_status': {row['status']: row['count'] for row in rows}
        }

    # ==================== ISSUE ATTACHMENTS ====================

    def add_attachment(self, issue_id: str, filename: str, original_filename: str,
                       file_size: int, mime_type: str, description: str = '',
                       extracted_text: str = '') -> int:
        """Add an attachment record. Returns the attachment ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO issue_attachments (issue_id, filename, original_filename, file_size, mime_type, description, extracted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (issue_id.upper(), filename, original_filename, file_size, mime_type, description, extracted_text))
        conn.commit()
        attachment_id = cursor.lastrowid
        conn.close()
        return attachment_id

    def get_attachments_for_issue(self, issue_id: str) -> List[Dict]:
        """Get all attachments for an issue."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM issue_attachments WHERE issue_id = ? ORDER BY uploaded_at DESC
        """, (issue_id.upper(),)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_attachment(self, attachment_id: int) -> Optional[Dict]:
        """Get a single attachment by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM issue_attachments WHERE id = ?", (attachment_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_attachment(self, attachment_id: int) -> bool:
        """Delete an attachment record."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM issue_attachments WHERE id = ?", (attachment_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_all_attachments_metadata(self) -> List[Dict]:
        """Get metadata for all attachments (for AI context)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT issue_id, original_filename, file_size, mime_type, description, uploaded_at
            FROM issue_attachments ORDER BY issue_id, uploaded_at
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def count_attachments_for_issue(self, issue_id: str) -> int:
        """Count attachments for an issue."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as count FROM issue_attachments WHERE issue_id = ?",
                          (issue_id.upper(),)).fetchone()
        conn.close()
        return row['count'] if row else 0

    # ==================== RISK ATTACHMENTS ====================

    def add_risk_attachment(self, risk_id: str, filename: str, original_filename: str,
                            file_size: int, mime_type: str, description: str = '',
                            category: str = 'planning', extracted_text: str = '') -> int:
        """Add a risk attachment record. Returns the attachment ID.
        Category can be: 'planning', 'de', 'oe'
        """
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO risk_attachments (risk_id, category, filename, original_filename, file_size, mime_type, description, extracted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (risk_id.upper(), category, filename, original_filename, file_size, mime_type, description, extracted_text))
        conn.commit()
        attachment_id = cursor.lastrowid
        conn.close()
        return attachment_id

    def get_attachments_for_risk(self, risk_id: str) -> List[Dict]:
        """Get all attachments for a risk."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM risk_attachments WHERE risk_id = ? ORDER BY uploaded_at DESC
        """, (risk_id.upper(),)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_risk_attachment(self, attachment_id: int) -> Optional[Dict]:
        """Get a single risk attachment by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM risk_attachments WHERE id = ?", (attachment_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_risk_attachment(self, attachment_id: int) -> bool:
        """Delete a risk attachment record."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM risk_attachments WHERE id = ?", (attachment_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_all_risk_attachments_metadata(self) -> List[Dict]:
        """Get metadata for all risk attachments (for AI context)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT risk_id, original_filename, file_size, mime_type, description, uploaded_at
            FROM risk_attachments ORDER BY risk_id, uploaded_at
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def count_attachments_for_risk(self, risk_id: str) -> int:
        """Count attachments for a risk."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as count FROM risk_attachments WHERE risk_id = ?",
                          (risk_id.upper(),)).fetchone()
        conn.close()
        return row['count'] if row else 0

    # ==================== AUDIT ATTACHMENTS ====================

    def add_audit_attachment(self, audit_id: int, filename: str, original_filename: str,
                             file_size: int, mime_type: str, description: str = '',
                             extracted_text: str = '') -> int:
        """Add an audit attachment record. Returns the attachment ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO audit_attachments (audit_id, filename, original_filename, file_size, mime_type, description, extracted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (audit_id, filename, original_filename, file_size, mime_type, description, extracted_text))
        conn.commit()
        attachment_id = cursor.lastrowid
        conn.close()
        return attachment_id

    def get_attachments_for_audit(self, audit_id: int) -> List[Dict]:
        """Get all attachments for an audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM audit_attachments WHERE audit_id = ? ORDER BY uploaded_at DESC
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audit_attachment(self, attachment_id: int) -> Optional[Dict]:
        """Get a single audit attachment by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM audit_attachments WHERE id = ?", (attachment_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_audit_attachment(self, attachment_id: int) -> bool:
        """Delete an audit attachment record."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM audit_attachments WHERE id = ?", (attachment_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_all_audit_attachments_metadata(self) -> List[Dict]:
        """Get metadata for all audit attachments (for AI context)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT audit_id, original_filename, file_size, mime_type, description, uploaded_at
            FROM audit_attachments ORDER BY audit_id, uploaded_at
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def count_attachments_for_audit(self, audit_id: int) -> int:
        """Count attachments for an audit."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as count FROM audit_attachments WHERE audit_id = ?",
                          (audit_id,)).fetchone()
        conn.close()
        return row['count'] if row else 0

    # ==================== AUDIT LIBRARY ====================

    def _init_vector_table(self):
        """Initialize sqlite-vec virtual table for vector search."""
        try:
            import sqlite_vec
            conn = self._get_conn()
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # Create vec0 virtual table for embeddings (384 dimensions for all-MiniLM-L6-v2)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS library_embeddings USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding float[384]
                )
            """)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Warning: Could not initialize vector table: {e}")
            return False

    def add_library_document(self, name: str, filename: str, original_filename: str,
                            doc_type: str = 'framework', source: str = None,
                            description: str = None, file_size: int = None,
                            mime_type: str = None) -> int:
        """Add a new library document. Returns the document ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO library_documents (name, filename, original_filename, doc_type,
                                          source, description, file_size, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, filename, original_filename, doc_type, source, description,
              file_size, mime_type))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        return doc_id

    def get_library_document(self, doc_id: int) -> Optional[Dict]:
        """Get a library document by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM library_documents WHERE id = ?", (doc_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_library_document_by_name(self, name: str) -> Optional[Dict]:
        """Get a library document by name."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM library_documents WHERE name = ?", (name,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_library_documents(self, doc_type: str = None) -> List[Dict]:
        """List all library documents, optionally filtered by type."""
        conn = self._get_conn()
        if doc_type:
            rows = conn.execute("""
                SELECT * FROM library_documents WHERE doc_type = ? ORDER BY name
            """, (doc_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM library_documents ORDER BY name").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_library_document(self, doc_id: int, **kwargs) -> bool:
        """Update a library document's metadata."""
        if not kwargs:
            return False

        allowed_fields = ['name', 'doc_type', 'source', 'description', 'total_chunks']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [doc_id]

        conn = self._get_conn()
        cursor = conn.execute(f"""
            UPDATE library_documents SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_library_document(self, doc_id: int) -> bool:
        """Delete a library document and all its chunks."""
        conn = self._get_conn()

        # Delete embeddings first (sqlite-vec virtual table)
        try:
            import sqlite_vec
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # Get chunk IDs for this document
            chunk_ids = conn.execute(
                "SELECT id FROM library_chunks WHERE document_id = ?", (doc_id,)
            ).fetchall()

            for (chunk_id,) in chunk_ids:
                conn.execute("DELETE FROM library_embeddings WHERE chunk_id = ?", (chunk_id,))
        except Exception as e:
            print(f"Warning: Could not delete embeddings: {e}")

        # Delete document (cascades to chunks)
        cursor = conn.execute("DELETE FROM library_documents WHERE id = ?", (doc_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def add_library_chunk(self, document_id: int, chunk_index: int, content: str,
                         section: str = None, token_count: int = None,
                         embedding: list = None) -> int:
        """Add a chunk to the library. Returns chunk ID."""
        conn = self._get_conn()

        # Insert chunk
        cursor = conn.execute("""
            INSERT INTO library_chunks (document_id, chunk_index, section, content, token_count)
            VALUES (?, ?, ?, ?, ?)
        """, (document_id, chunk_index, section, content, token_count))
        chunk_id = cursor.lastrowid

        # Add embedding if provided
        if embedding:
            try:
                import sqlite_vec
                import struct
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)

                # Pack embedding as binary
                embedding_blob = struct.pack(f'{len(embedding)}f', *embedding)
                conn.execute("""
                    INSERT INTO library_embeddings (chunk_id, embedding)
                    VALUES (?, ?)
                """, (chunk_id, embedding_blob))
            except Exception as e:
                print(f"Warning: Could not add embedding: {e}")

        conn.commit()
        conn.close()
        return chunk_id

    def get_library_chunks(self, document_id: int) -> List[Dict]:
        """Get all chunks for a document."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM library_chunks WHERE document_id = ? ORDER BY chunk_index
        """, (document_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_library(self, query_embedding: list, limit: int = 5) -> List[Dict]:
        """Search the library using vector similarity. Returns relevant chunks with metadata."""
        try:
            import sqlite_vec
            import struct

            conn = self._get_conn()
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # Pack query embedding
            query_blob = struct.pack(f'{len(query_embedding)}f', *query_embedding)

            # Vector search with join to get full context
            rows = conn.execute("""
                SELECT
                    c.id as chunk_id,
                    c.content,
                    c.section,
                    c.chunk_index,
                    d.id as document_id,
                    d.name as document_name,
                    d.source,
                    d.doc_type,
                    e.distance
                FROM library_embeddings e
                JOIN library_chunks c ON e.chunk_id = c.id
                JOIN library_documents d ON c.document_id = d.id
                WHERE e.embedding MATCH ?
                ORDER BY e.distance
                LIMIT ?
            """, (query_blob, limit)).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error in library search: {e}")
            return []

    def search_library_keyword(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Fallback keyword search when vector search isn't available.

        Searches for any of the words in the query (OR logic) and ranks by match count.
        """
        conn = self._get_conn()

        # Split query into words, filter out short/common words
        words = [w.strip().lower() for w in keyword.split() if len(w.strip()) > 2]
        if not words:
            words = [keyword.lower()]

        # Build query with OR conditions for each word
        conditions = []
        params = []
        for word in words:
            conditions.append("(LOWER(c.content) LIKE ? OR LOWER(c.section) LIKE ?)")
            params.extend([f'%{word}%', f'%{word}%'])

        where_clause = " OR ".join(conditions)
        params.append(limit)

        rows = conn.execute(f"""
            SELECT
                c.id as chunk_id,
                c.content,
                c.section,
                c.chunk_index,
                d.id as document_id,
                d.name as document_name,
                d.source,
                d.doc_type
            FROM library_chunks c
            JOIN library_documents d ON c.document_id = d.id
            WHERE {where_clause}
            ORDER BY d.name, c.chunk_index
            LIMIT ?
        """, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_library_stats(self) -> Dict:
        """Get library statistics."""
        conn = self._get_conn()
        doc_count = conn.execute("SELECT COUNT(*) FROM library_documents").fetchone()[0]
        chunk_count = conn.execute("SELECT COUNT(*) FROM library_chunks").fetchone()[0]

        # Get counts by type
        type_counts = conn.execute("""
            SELECT doc_type, COUNT(*) as count FROM library_documents GROUP BY doc_type
        """).fetchall()

        conn.close()
        return {
            'total_documents': doc_count,
            'total_chunks': chunk_count,
            'by_type': {row['doc_type']: row['count'] for row in type_counts}
        }

    # ==================== USERS ====================

    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, email, name, is_active, is_admin, created_at, updated_at
            FROM users ORDER BY name
        """).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get a user by ID."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT id, email, name, password_hash, is_active, is_admin, created_at, updated_at, role
            FROM users WHERE id = ?
        """, (user_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get a user by email (for login)."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT id, email, name, password_hash, is_active, is_admin, created_at, updated_at, role
            FROM users WHERE email = ?
        """, (email.lower(),)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_user(self, email: str, name: str, password_hash: str,
                    is_active: int = 1, is_admin: int = 0) -> int:
        """Create a new user. Returns the user ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO users (email, name, password_hash, is_active, is_admin)
            VALUES (?, ?, ?, ?, ?)
        """, (email.lower(), name, password_hash, is_active, is_admin))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update a user. Allowed fields: name, email, password_hash, is_active, is_admin."""
        allowed = {'name', 'email', 'password_hash', 'is_active', 'is_admin'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Lowercase email if provided
        if 'email' in updates:
            updates['email'] = updates['email'].lower()

        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())

        conn = self._get_conn()
        cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?",
                              (*updates.values(), user_id))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (also removes their memberships via CASCADE)."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ==================== ROLES ====================

    def get_all_roles(self) -> List[Dict]:
        """Get all roles."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM roles ORDER BY id").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_role_by_id(self, role_id: int) -> Optional[Dict]:
        """Get a role by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_role_by_name(self, name: str) -> Optional[Dict]:
        """Get a role by name."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM roles WHERE name = ?", (name.lower(),)).fetchone()
        conn.close()
        return dict(row) if row else None

    # ==================== AUDIT MEMBERSHIPS ====================

    def get_audit_memberships(self, audit_id: int) -> List[Dict]:
        """Get all memberships for an audit with user and role details."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                am.id, am.audit_id, am.user_id, am.role_id, am.created_at,
                u.email, u.name as user_name, u.is_active,
                r.name as role_name, r.description as role_description
            FROM audit_memberships am
            JOIN users u ON am.user_id = u.id
            JOIN roles r ON am.role_id = r.id
            WHERE am.audit_id = ?
            ORDER BY r.id, u.name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audit_membership(self, user_id: int, audit_id: int) -> Optional[Dict]:
        """Get a specific user's membership for an audit."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT
                am.id, am.audit_id, am.user_id, am.role_id, am.created_at,
                r.name as role_name
            FROM audit_memberships am
            JOIN roles r ON am.role_id = r.id
            WHERE am.user_id = ? AND am.audit_id = ?
        """, (user_id, audit_id)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_audit_ids(self, user_id: int) -> List[int]:
        """Get list of audit IDs a user has access to."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT audit_id FROM audit_memberships WHERE user_id = ?
        """, (user_id,)).fetchall()
        conn.close()
        return [row['audit_id'] for row in rows]

    def get_user_memberships(self, user_id: int) -> List[Dict]:
        """Get all audit memberships for a user with audit and role details."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT
                am.id, am.audit_id, am.user_id, am.role_id, am.created_at,
                a.title as audit_title, a.status as audit_status,
                r.name as role_name
            FROM audit_memberships am
            JOIN audits a ON am.audit_id = a.id
            JOIN roles r ON am.role_id = r.id
            WHERE am.user_id = ?
            ORDER BY a.title
        """, (user_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_audit_membership(self, audit_id: int, user_id: int, role_id: int) -> int:
        """Add a user to an audit with a role. Returns membership ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO audit_memberships (audit_id, user_id, role_id)
            VALUES (?, ?, ?)
        """, (audit_id, user_id, role_id))
        conn.commit()
        membership_id = cursor.lastrowid
        conn.close()
        return membership_id

    def update_audit_membership(self, audit_id: int, user_id: int, role_id: int) -> bool:
        """Update a user's role in an audit."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE audit_memberships SET role_id = ?
            WHERE audit_id = ? AND user_id = ?
        """, (role_id, audit_id, user_id))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def remove_audit_membership(self, audit_id: int, user_id: int) -> bool:
        """Remove a user from an audit."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM audit_memberships WHERE audit_id = ? AND user_id = ?
        """, (audit_id, user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def user_has_audit_access(self, user_id: int, audit_id: int, min_role: str = 'viewer') -> bool:
        """Check if a user has at least the specified role level for an audit.

        Role hierarchy (higher number = more permissions):
        - viewer (4): read-only
        - reviewer (3): read + comments
        - auditor (2): edit assigned audits
        - admin (1): full access

        Returns True if user's role level is <= min_role level (lower id = higher permission).
        """
        membership = self.get_audit_membership(user_id, audit_id)
        if not membership:
            return False

        role_hierarchy = {'admin': 1, 'auditor': 2, 'reviewer': 3, 'viewer': 4}
        user_level = role_hierarchy.get(membership['role_name'], 999)
        required_level = role_hierarchy.get(min_role, 999)

        return user_level <= required_level

    # ==================== SCOPED QUERIES (BY AUDIT) ====================

    def get_risks_by_audit(self, audit_id: int) -> List[Dict]:
        """Get all risks for a specific audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM risks WHERE audit_id = ? ORDER BY risk_id
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_risks_by_audits(self, audit_ids: List[int]) -> List[Dict]:
        """Get all risks for multiple audits."""
        if not audit_ids:
            return []
        conn = self._get_conn()
        placeholders = ','.join('?' * len(audit_ids))
        rows = conn.execute(f"""
            SELECT * FROM risks WHERE audit_id IN ({placeholders}) ORDER BY risk_id
        """, audit_ids).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_issues_by_audit(self, audit_id: int) -> List[Dict]:
        """Get all issues for a specific audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM issues WHERE audit_id = ? ORDER BY issue_id
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_issues_by_audits(self, audit_ids: List[int]) -> List[Dict]:
        """Get all issues for multiple audits."""
        if not audit_ids:
            return []
        conn = self._get_conn()
        placeholders = ','.join('?' * len(audit_ids))
        rows = conn.execute(f"""
            SELECT * FROM issues WHERE audit_id IN ({placeholders}) ORDER BY issue_id
        """, audit_ids).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_tasks_by_audit(self, audit_id: int) -> List[Dict]:
        """Get all tasks for a specific audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            WHERE t.audit_id = ?
            ORDER BY t.created_at
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_tasks_by_audits(self, audit_ids: List[int]) -> List[Dict]:
        """Get all tasks for multiple audits."""
        if not audit_ids:
            return []
        conn = self._get_conn()
        placeholders = ','.join('?' * len(audit_ids))
        rows = conn.execute(f"""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            WHERE t.audit_id IN ({placeholders})
            ORDER BY t.created_at
        """, audit_ids).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_flowcharts_by_audit(self, audit_id: int) -> List[Dict]:
        """Get all flowcharts for a specific audit (metadata only)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, name, risk_id, created_at, updated_at
            FROM flowcharts WHERE audit_id = ? ORDER BY name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_test_documents_by_audit(self, audit_id: int) -> List[Dict]:
        """Get all test document metadata for a specific audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT td.*, r.risk_id as risk_code
            FROM test_documents td
            JOIN risks r ON td.risk_id = r.id
            WHERE td.audit_id = ?
            ORDER BY r.risk_id, td.doc_type
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_context_for_audit(self, audit_id: int) -> Dict:
        """Get full context for a specific audit (for AI)."""
        audit = self.get_audit(audit_id)
        risks = self.get_risks_by_audit(audit_id)
        issues = self.get_issues_by_audit(audit_id)
        tasks = self.get_tasks_by_audit(audit_id)
        flowcharts = self.get_flowcharts_by_audit(audit_id)

        # Get attachment counts
        conn = self._get_conn()
        risk_attachment_count = conn.execute(
            "SELECT COUNT(*) FROM risk_attachments WHERE audit_id = ?", (audit_id,)
        ).fetchone()[0]
        issue_attachment_count = conn.execute(
            "SELECT COUNT(*) FROM issue_attachments WHERE audit_id = ?", (audit_id,)
        ).fetchone()[0]
        conn.close()

        # Add documentation status to issues
        issues_with_doc_status = []
        for issue in issues:
            issue_copy = dict(issue)
            issue_copy['has_documentation'] = bool(issue.get('documentation', '').strip())
            if 'documentation' in issue_copy:
                del issue_copy['documentation']
            issues_with_doc_status.append(issue_copy)

        return {
            'audit': audit,
            'risks': risks,
            'issues': issues_with_doc_status,
            'tasks': tasks,
            'flowcharts': [{'name': f['name'], 'risk_id': f['risk_id']} for f in flowcharts],
            'risk_attachment_count': risk_attachment_count,
            'issue_attachment_count': issue_attachment_count,
            'risk_summary': {
                'total': len(risks),
                'by_status': {}
            },
            'issue_summary': {
                'total': len(issues),
                'by_status': {}
            },
            'task_summary': {
                'total': len(tasks),
                'by_column': {}
            }
        }

    def get_context_for_audits(self, audit_ids: List[int]) -> Dict:
        """Get aggregated context for multiple audits (for AI)."""
        if not audit_ids:
            return {
                'audits': [],
                'risks': [],
                'issues': [],
                'tasks': [],
                'flowcharts': [],
                'schema': self.get_schema()
            }

        conn = self._get_conn()

        # Get audits
        placeholders = ','.join('?' * len(audit_ids))
        audits = [dict(row) for row in conn.execute(f"""
            SELECT * FROM audits WHERE id IN ({placeholders})
        """, audit_ids).fetchall()]

        # Get risks
        risks = [dict(row) for row in conn.execute(f"""
            SELECT * FROM risks WHERE audit_id IN ({placeholders}) ORDER BY risk_id
        """, audit_ids).fetchall()]

        # Get issues
        issues_raw = conn.execute(f"""
            SELECT * FROM issues WHERE audit_id IN ({placeholders}) ORDER BY issue_id
        """, audit_ids).fetchall()
        issues = []
        for row in issues_raw:
            issue = dict(row)
            issue['has_documentation'] = bool(issue.get('documentation', '').strip())
            if 'documentation' in issue:
                del issue['documentation']
            issues.append(issue)

        # Get tasks
        tasks = [dict(row) for row in conn.execute(f"""
            SELECT t.*, r.risk_id as linked_risk_id
            FROM tasks t
            LEFT JOIN risks r ON t.risk_id = r.id
            WHERE t.audit_id IN ({placeholders})
            ORDER BY t.created_at
        """, audit_ids).fetchall()]

        # Get flowcharts
        flowcharts = [dict(row) for row in conn.execute(f"""
            SELECT id, name, risk_id FROM flowcharts
            WHERE audit_id IN ({placeholders}) ORDER BY name
        """, audit_ids).fetchall()]

        conn.close()

        return {
            'schema': self.get_schema(),
            'audits': audits,
            'risks': risks,
            'issues': issues,
            'tasks': tasks,
            'flowcharts': [{'name': f['name'], 'risk_id': f['risk_id']} for f in flowcharts],
            'risk_summary': {
                'total': len(risks),
                'by_status': self._count_by_field(risks, 'status')
            },
            'issue_summary': {
                'total': len(issues),
                'by_status': self._count_by_field(issues, 'status')
            },
            'task_summary': {
                'total': len(tasks),
                'by_column': self._count_by_field(tasks, 'column_id')
            }
        }

    def _count_by_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """Helper to count items by a field value."""
        counts = {}
        for item in items:
            value = item.get(field) or 'unknown'
            counts[value] = counts.get(value, 0) + 1
        return counts

    def get_accessible_audits(self, user_id: int, is_admin: bool = False) -> List[Dict]:
        """Get audits accessible to a user.

        Admins see all audits.
        Non-admins see audits where they are:
        - A team member (audit_memberships table), OR
        - Assigned as a viewer (audit_viewers table)
        """
        if is_admin:
            return self.get_all_audits()

        conn = self._get_conn()
        # Get audits from both memberships and viewer assignments
        rows = conn.execute("""
            SELECT DISTINCT a.* FROM audits a
            LEFT JOIN audit_memberships am ON a.id = am.audit_id AND am.user_id = ?
            LEFT JOIN audit_viewers av ON a.id = av.audit_id AND av.viewer_user_id = ?
            WHERE am.user_id IS NOT NULL OR av.viewer_user_id IS NOT NULL
            ORDER BY a.title
        """, (user_id, user_id)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== AI QUERY HELPERS ====================

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute a raw SQL query (for AI-generated queries).
        READ-ONLY - only SELECT statements allowed.
        Validates query to prevent SQL injection attacks."""
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()

        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            raise ValueError("Only SELECT queries allowed")

        # Strip SQL comments that could hide malicious keywords
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
        sql_no_comments = re.sub(r'--.*$', '', sql_no_comments, flags=re.MULTILINE)
        sql_upper = sql_no_comments.upper()

        # Block dangerous keywords that could modify data or exfiltrate info
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'ATTACH',
            'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX',
            'UNION',  # Prevent data exfiltration via UNION queries
            'INTO',   # Prevent SELECT INTO
            'LOAD',   # Prevent LOAD DATA
            'OUTFILE' # Prevent file writes
        ]
        for keyword in dangerous_keywords:
            # Check for keyword as whole word (not part of column name)
            if re.search(rf'\b{keyword}\b', sql_upper):
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        # Block statement terminators that could chain queries
        if ';' in sql_clean[:-1]:  # Allow trailing semicolon
            raise ValueError("Multiple statements not allowed")

        with self._connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def get_schema(self) -> str:
        """Return database schema for AI context."""
        return """
DATABASE SCHEMA:

TABLE risks (RACM - Risk and Control Matrix):
  - id: INTEGER PRIMARY KEY
  - risk_id: TEXT (e.g., 'R001', 'R002')
  - risk: TEXT (risk description)
  - control_id: TEXT
  - control_owner: TEXT
  - design_effectiveness_testing: TEXT
  - design_effectiveness_conclusion: TEXT
  - operational_effectiveness_test: TEXT
  - operational_effectiveness_conclusion: TEXT
  - status: TEXT (Not Complete, Effective, Not Effective)
  - ready_for_review: INTEGER (0 or 1)
  - reviewer: TEXT
  - raise_issue: INTEGER (0 or 1)
  - closed: INTEGER (0 or 1)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE tasks (Kanban board items - for individual audit execution):
  - id: INTEGER PRIMARY KEY
  - title: TEXT
  - description: TEXT
  - priority: TEXT (low, medium, high)
  - assignee: TEXT
  - column_id: TEXT (planning, fieldwork, testing, review, complete)
  - risk_id: INTEGER (FK to risks.id)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE audits (Annual Audit Plan - all audits planned for the year):
  - id: INTEGER PRIMARY KEY
  - title: TEXT (audit name, e.g., 'IT Security Audit', 'Financial Controls Audit')
  - description: TEXT (scope and objectives)
  - audit_area: TEXT (IT, Finance, Operations, HR, Compliance, Other)
  - owner: TEXT (lead auditor)
  - planned_start: DATE (planned start date)
  - planned_end: DATE (planned end date)
  - actual_start: DATE (actual start date)
  - actual_end: DATE (actual completion date)
  - quarter: TEXT (Q1, Q2, Q3, Q4 - fiscal quarter)
  - status: TEXT (planning, in_progress, fieldwork, review, complete)
  - priority: TEXT (low, medium, high)
  - estimated_hours: REAL (estimated effort)
  - actual_hours: REAL (actual effort)
  - risk_rating: TEXT (low, medium, high - audit risk level)
  - notes: TEXT
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

USEFUL QUERIES FOR ANNUAL AUDIT PLAN:
  - Audits by quarter: SELECT * FROM audits WHERE quarter = 'Q1'
  - Audits in progress: SELECT * FROM audits WHERE status IN ('in_progress', 'fieldwork')
  - Overdue audits: SELECT * FROM audits WHERE planned_end < DATE('now') AND status != 'complete'
  - Workload by owner: SELECT owner, COUNT(*) as count, SUM(estimated_hours) as hours FROM audits GROUP BY owner
  - Progress summary: SELECT status, COUNT(*) FROM audits GROUP BY status

TABLE flowcharts (Process diagrams):
  - id: INTEGER PRIMARY KEY
  - name: TEXT (unique identifier)
  - data: JSON (Drawflow format with nodes)
  - risk_id: INTEGER (FK to risks.id)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE test_documents (Working papers - DE/OE testing documentation):
  - id: INTEGER PRIMARY KEY
  - risk_id: INTEGER (FK to risks.id)
  - doc_type: TEXT ('de_testing' or 'oe_testing')
  - content: TEXT (HTML/rich text content)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE issues (Issue Log - linked to RACM risks):
  - id: INTEGER PRIMARY KEY
  - issue_id: TEXT (e.g., 'ISS-001', 'ISS-002')
  - risk_id: TEXT (links to risks.risk_id)
  - title: TEXT
  - description: TEXT
  - severity: TEXT (Low, Medium, High, Critical)
  - status: TEXT (Open, In Progress, Resolved, Closed)
  - assigned_to: TEXT
  - due_date: DATE
  - documentation: TEXT (rich text/HTML - evidence and detailed findings)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE issue_attachments (Evidence files for issues):
  - id: INTEGER PRIMARY KEY
  - issue_id: TEXT
  - filename: TEXT
  - original_filename: TEXT
  - file_size: INTEGER
  - mime_type: TEXT
  - description: TEXT
  - extracted_text: TEXT
  - uploaded_at: TIMESTAMP

TABLE risk_attachments (Evidence files for risks):
  - id: INTEGER PRIMARY KEY
  - risk_id: TEXT
  - category: TEXT (planning, de, oe)
  - filename: TEXT
  - original_filename: TEXT
  - file_size: INTEGER
  - mime_type: TEXT
  - description: TEXT
  - extracted_text: TEXT
  - uploaded_at: TIMESTAMP

RELATIONSHIPS:
  - tasks.risk_id -> risks.id (many tasks can link to one risk)
  - flowcharts.risk_id -> risks.id (flowchart can document a risk's control)
  - test_documents.risk_id -> risks.id (each risk can have DE and OE testing docs)
  - issues.risk_id -> risks.risk_id (issues are raised against RACM risks)
  - issue_attachments.issue_id -> issues.issue_id
  - risk_attachments.risk_id -> risks.risk_id
"""

    def get_full_context(self) -> Dict:
        """Get full database context for AI."""
        flowcharts = self.get_all_flowcharts()
        test_docs = self.get_all_test_documents_metadata()
        issues = self.get_all_issues()

        # Add documentation status to issues
        issues_with_doc_status = []
        for issue in issues:
            issue_copy = dict(issue)
            issue_copy['has_documentation'] = bool(issue.get('documentation', '').strip())
            # Don't include full documentation in context - AI should use tool to read it
            if 'documentation' in issue_copy:
                del issue_copy['documentation']
            issues_with_doc_status.append(issue_copy)

        # Get attachment metadata
        issue_attachments = self.get_all_attachments_metadata()
        risk_attachments = self.get_all_risk_attachments_metadata()

        return {
            'schema': self.get_schema(),
            'risk_summary': self.get_risk_summary(),
            'task_summary': self.get_task_summary(),
            'issue_summary': self.get_issue_summary(),
            'audit_summary': self.get_audit_summary(),
            'flowchart_count': len(flowcharts),
            'test_doc_count': len(test_docs),
            'issue_attachment_count': len(issue_attachments),
            'risk_attachment_count': len(risk_attachments),
            'risks': self.get_all_risks(),
            'tasks': self.get_all_tasks(),
            'audits': self.get_all_audits(),  # Annual audit plan
            'issues': issues_with_doc_status,  # With has_documentation flag
            'flowcharts': [{'name': f['name'], 'risk_id': f['risk_id']}
                          for f in flowcharts],
            'test_documents': test_docs,  # Metadata only - use tools to read full content
            'issue_attachments': issue_attachments,  # File evidence attached to issues
            'risk_attachments': risk_attachments  # File evidence attached to risks
        }

    # ==================== IMPORT/EXPORT ====================

    def export_all(self) -> Dict:
        """Export entire database as JSON (for backup)."""
        conn = self._get_conn()

        risks = [dict(r) for r in conn.execute("SELECT * FROM risks").fetchall()]
        tasks = [dict(t) for t in conn.execute("SELECT * FROM tasks").fetchall()]
        flowcharts = []
        for row in conn.execute("SELECT * FROM flowcharts").fetchall():
            f = dict(row)
            f['data'] = json.loads(f['data'])
            flowcharts.append(f)

        conn.close()
        return {
            'exported_at': datetime.now().isoformat(),
            'risks': risks,
            'tasks': tasks,
            'flowcharts': flowcharts
        }

    def import_all(self, data: Dict, clear_existing: bool = False):
        """Import data from JSON export."""
        conn = self._get_conn()

        if clear_existing:
            conn.execute("DELETE FROM flowcharts")
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM risks")

        # Import risks
        for risk in data.get('risks', []):
            conn.execute("""
                INSERT OR REPLACE INTO risks
                (id, risk_id, risk_description, control_description, control_owner, frequency, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (risk.get('id'), risk['risk_id'], risk.get('risk_description', ''),
                  risk.get('control_description', ''), risk.get('control_owner', ''),
                  risk.get('frequency', ''), risk.get('status', 'Not Tested')))

        # Import tasks
        for task in data.get('tasks', []):
            conn.execute("""
                INSERT OR REPLACE INTO tasks
                (id, title, description, priority, assignee, column_id, risk_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task.get('id'), task['title'], task.get('description', ''),
                  task.get('priority', 'medium'), task.get('assignee', ''),
                  task.get('column_id', 'planning'), task.get('risk_id')))

        # Import flowcharts
        for fc in data.get('flowcharts', []):
            conn.execute("""
                INSERT OR REPLACE INTO flowcharts (id, name, data, risk_id)
                VALUES (?, ?, ?, ?)
            """, (fc.get('id'), fc['name'], json.dumps(fc['data']), fc.get('risk_id')))

        conn.commit()
        conn.close()

    # ==================== SPREADSHEET COMPATIBILITY ====================

    def get_as_spreadsheet(self) -> List[List]:
        """Get risks in spreadsheet format (for backward compatibility)."""
        risks = self.get_all_risks()

        rows = []
        for r in risks:
            # Find linked flowchart and task
            conn = self._get_conn()
            fc = conn.execute("SELECT name FROM flowcharts WHERE risk_id = ?", (r['id'],)).fetchone()
            task = conn.execute("SELECT title FROM tasks WHERE risk_id = ?", (r['id'],)).fetchone()
            conn.close()

            rows.append([
                r['risk_id'],
                r['risk'] or '',
                r['control_id'] or '',
                r['control_owner'] or '',
                r['design_effectiveness_testing'] or '',
                r['design_effectiveness_conclusion'] or '',
                r['operational_effectiveness_test'] or '',
                r['operational_effectiveness_conclusion'] or '',
                r['status'] or 'Not Complete',
                r['ready_for_review'],
                r['reviewer'] or '',
                r['raise_issue'],
                r['closed'],
                fc['name'] if fc else '',
                task['title'] if task else ''
            ])
        return rows

    def save_from_spreadsheet(self, data: List[List]):
        """Save risks from spreadsheet format (for backward compatibility)."""
        if not data or len(data) < 1:
            return

        for row in data:
            if len(row) >= 1 and row[0]:  # Must have risk_id at minimum
                risk_id = row[0]
                existing = self.get_risk(risk_id)

                # Convert checkbox values (True/False/1/0) to int
                def to_int(val):
                    if isinstance(val, bool):
                        return 1 if val else 0
                    if isinstance(val, int):
                        return val
                    return 0

                ready_for_review = to_int(row[9]) if len(row) > 9 else 0
                raise_issue = to_int(row[11]) if len(row) > 11 else 0
                closed = to_int(row[12]) if len(row) > 12 else 0

                if existing:
                    self.update_risk(
                        risk_id,
                        risk=row[1] if len(row) > 1 else '',
                        control_id=row[2] if len(row) > 2 else '',
                        control_owner=row[3] if len(row) > 3 else '',
                        design_effectiveness_testing=row[4] if len(row) > 4 else '',
                        design_effectiveness_conclusion=row[5] if len(row) > 5 else '',
                        operational_effectiveness_test=row[6] if len(row) > 6 else '',
                        operational_effectiveness_conclusion=row[7] if len(row) > 7 else '',
                        status=row[8] if len(row) > 8 else 'Not Complete',
                        ready_for_review=ready_for_review,
                        reviewer=row[10] if len(row) > 10 else '',
                        raise_issue=raise_issue,
                        closed=closed
                    )
                else:
                    self.create_risk(
                        risk_id=risk_id,
                        risk=row[1] if len(row) > 1 else '',
                        control_id=row[2] if len(row) > 2 else '',
                        control_owner=row[3] if len(row) > 3 else '',
                        design_effectiveness_testing=row[4] if len(row) > 4 else '',
                        design_effectiveness_conclusion=row[5] if len(row) > 5 else '',
                        operational_effectiveness_test=row[6] if len(row) > 6 else '',
                        operational_effectiveness_conclusion=row[7] if len(row) > 7 else '',
                        status=row[8] if len(row) > 8 else 'Not Complete',
                        ready_for_review=ready_for_review,
                        reviewer=row[10] if len(row) > 10 else '',
                        raise_issue=raise_issue,
                        closed=closed
                    )

    def get_kanban_format(self) -> Dict:
        """Get tasks in kanban board format (for backward compatibility)."""
        columns = ['planning', 'fieldwork', 'testing', 'review', 'complete']
        board = {
            'name': 'Audit Plan',
            'columns': []
        }

        for col_id in columns:
            tasks = self.get_tasks_by_column(col_id)
            board['columns'].append({
                'id': col_id,
                'title': col_id.title(),
                'items': [
                    {
                        'id': str(t['id']),
                        'title': t['title'],
                        'description': t['description'] or '',
                        'priority': t['priority'] or 'medium',
                        'assignee': t['assignee'] or '',
                        'risk_id': t['linked_risk_id'] or ''
                    }
                    for t in tasks
                ]
            })

        return {'boards': {'default': board}}

    # ==================== WORKFLOW STATE TRANSITIONS ====================

    def get_record_with_audit(self, record_type: str, record_id: int) -> Optional[Dict]:
        """Get a record with its associated audit data."""
        table = 'risks' if record_type == 'risk' else 'issues'
        conn = self._get_conn()
        row = conn.execute(f"""
            SELECT r.*, a.auditor_id, a.reviewer_id, a.title as audit_title
            FROM {table} r
            LEFT JOIN audits a ON r.audit_id = a.id
            WHERE r.id = ?
        """, (record_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_record_status(self, record_type: str, record_id: int,
                            new_status: str, new_owner_role: str,
                            user_id: int, **extra_fields) -> bool:
        """Update a record's workflow status atomically."""
        table = 'risks' if record_type == 'risk' else 'issues'

        # Build update fields
        fields = {
            'record_status': new_status,
            'current_owner_role': new_owner_role,
            'updated_by': user_id,
            'updated_at': datetime.now().isoformat()
        }
        fields.update(extra_fields)

        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())

        with self._connection() as conn:
            cursor = conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE id = ?",
                (*fields.values(), record_id)
            )
            return cursor.rowcount > 0

    def create_state_history(self, record_type: str, record_id: int,
                            from_status: Optional[str], to_status: str,
                            action: str, performed_by: int,
                            notes: str = None, reason: str = None) -> int:
        """Create a state history entry."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO record_state_history
                (record_type, record_id, from_status, to_status, action,
                 performed_by, notes, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_type, record_id, from_status, to_status, action,
              performed_by, notes, reason))
        conn.commit()
        history_id = cursor.lastrowid
        conn.close()
        return history_id

    def get_record_history(self, record_type: str, record_id: int) -> List[Dict]:
        """Get the state transition history for a record."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT h.*, u.name as performed_by_name, u.email as performed_by_email
            FROM record_state_history h
            LEFT JOIN users u ON h.performed_by = u.id
            WHERE h.record_type = ? AND h.record_id = ?
            ORDER BY h.performed_at DESC
        """, (record_type, record_id)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_state_history(self, filters: Dict = None) -> List[Dict]:
        """Get all state history entries with optional filters."""
        query = """
            SELECT h.*, u.name as performed_by_name, u.email as performed_by_email
            FROM record_state_history h
            LEFT JOIN users u ON h.performed_by = u.id
            WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('from_date'):
                query += " AND h.performed_at >= ?"
                params.append(filters['from_date'])
            if filters.get('to_date'):
                query += " AND h.performed_at <= ?"
                params.append(filters['to_date'])
            if filters.get('user_id'):
                query += " AND h.performed_by = ?"
                params.append(filters['user_id'])
            if filters.get('action'):
                query += " AND h.action = ?"
                params.append(filters['action'])
            if filters.get('record_type'):
                query += " AND h.record_type = ?"
                params.append(filters['record_type'])

        query += " ORDER BY h.performed_at DESC"

        conn = self._get_conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== AUDIT VIEWERS ====================

    def get_audit_viewers(self, audit_id: int) -> List[Dict]:
        """Get all viewers for an audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT av.*, u.name as viewer_name, u.email as viewer_email,
                   g.name as granted_by_name
            FROM audit_viewers av
            JOIN users u ON av.viewer_user_id = u.id
            LEFT JOIN users g ON av.granted_by = g.id
            WHERE av.audit_id = ?
            ORDER BY av.granted_at DESC
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_audit_viewer(self, audit_id: int, viewer_user_id: int,
                        granted_by: int) -> int:
        """Add a viewer to an audit. Returns viewer record ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT OR IGNORE INTO audit_viewers (audit_id, viewer_user_id, granted_by)
            VALUES (?, ?, ?)
        """, (audit_id, viewer_user_id, granted_by))
        conn.commit()
        viewer_id = cursor.lastrowid
        conn.close()
        return viewer_id

    def remove_audit_viewer(self, audit_id: int, viewer_user_id: int) -> bool:
        """Remove a viewer from an audit."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM audit_viewers
            WHERE audit_id = ? AND viewer_user_id = ?
        """, (audit_id, viewer_user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def is_viewer_of_audit(self, user_id: int, audit_id: int) -> bool:
        """Check if a user is a viewer of an audit."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT 1 FROM audit_viewers
            WHERE audit_id = ? AND viewer_user_id = ?
        """, (audit_id, user_id)).fetchone()
        conn.close()
        return row is not None

    def get_audit_viewers_list(self, audit_id: int) -> List[Dict]:
        """Get all viewers assigned to an audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT av.id, av.viewer_user_id as user_id, av.granted_at,
                   u.name as user_name, u.email as user_email
            FROM audit_viewers av
            JOIN users u ON av.viewer_user_id = u.id
            WHERE av.audit_id = ?
            ORDER BY u.name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_viewer_to_audit(self, audit_id: int, user_id: int, granted_by: int = None) -> int:
        """Add a viewer to an audit. Returns new ID or -1 if already exists."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO audit_viewers (audit_id, viewer_user_id, granted_by)
                VALUES (?, ?, ?)
            """, (audit_id, user_id, granted_by))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return new_id
        except sqlite3.IntegrityError:
            conn.close()
            return -1  # Already exists

    def remove_viewer_from_audit(self, audit_id: int, user_id: int) -> bool:
        """Remove a viewer from an audit."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM audit_viewers
            WHERE audit_id = ? AND viewer_user_id = ?
        """, (audit_id, user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ==================== AUDIT ASSIGNMENTS ====================

    def update_audit_assignment(self, audit_id: int, auditor_id: int = None,
                               reviewer_id: int = None) -> bool:
        """Update auditor and/or reviewer assignment for an audit (legacy single assignment)."""
        updates = {}
        if auditor_id is not None:
            updates['auditor_id'] = auditor_id
        if reviewer_id is not None:
            updates['reviewer_id'] = reviewer_id

        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())

        conn = self._get_conn()
        cursor = conn.execute(
            f"UPDATE audits SET {set_clause} WHERE id = ?",
            (*updates.values(), audit_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def get_audits_by_auditor(self, auditor_id: int) -> List[Dict]:
        """Get all audits where user is assigned as auditor (via audit_team)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT DISTINCT a.* FROM audits a
            JOIN audit_team at ON a.id = at.audit_id
            WHERE at.user_id = ? AND at.team_role = 'auditor'
            ORDER BY a.title
        """, (auditor_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audits_by_reviewer(self, reviewer_id: int) -> List[Dict]:
        """Get all audits where user is assigned as reviewer (via audit_team)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT DISTINCT a.* FROM audits a
            JOIN audit_team at ON a.id = at.audit_id
            WHERE at.user_id = ? AND at.team_role = 'reviewer'
            ORDER BY a.title
        """, (reviewer_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== AUDIT TEAM (MULTI-ASSIGNMENT) ====================

    def get_audit_team(self, audit_id: int) -> List[Dict]:
        """Get all team members (auditors and reviewers) for an audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT at.id, at.audit_id, at.user_id, at.team_role, at.assigned_at,
                   u.name as user_name, u.email as user_email
            FROM audit_team at
            JOIN users u ON at.user_id = u.id
            WHERE at.audit_id = ?
            ORDER BY at.team_role, u.name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audit_auditors(self, audit_id: int) -> List[Dict]:
        """Get all auditors assigned to an audit."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT at.id, at.user_id, u.name as user_name, u.email as user_email
            FROM audit_team at
            JOIN users u ON at.user_id = u.id
            WHERE at.audit_id = ? AND at.team_role = 'auditor'
            ORDER BY u.name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_audit_reviewers(self, audit_id: int) -> List[Dict]:
        """Get all reviewers assigned to an audit (for reviewer selection dropdown)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT at.id, at.user_id, u.name as user_name, u.email as user_email
            FROM audit_team at
            JOIN users u ON at.user_id = u.id
            WHERE at.audit_id = ? AND at.team_role = 'reviewer'
            ORDER BY u.name
        """, (audit_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_to_audit_team(self, audit_id: int, user_id: int, team_role: str,
                         assigned_by: int = None) -> int:
        """Add a user to an audit team. Returns new membership ID or -1 if exists."""
        if team_role not in ('auditor', 'reviewer'):
            raise ValueError("team_role must be 'auditor' or 'reviewer'")

        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO audit_team (audit_id, user_id, team_role, assigned_by)
                VALUES (?, ?, ?, ?)
            """, (audit_id, user_id, team_role, assigned_by))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return new_id
        except sqlite3.IntegrityError:
            conn.close()
            return -1  # Already exists

    def remove_from_audit_team(self, audit_id: int, user_id: int, team_role: str = None) -> bool:
        """Remove a user from an audit team. If team_role is None, removes all roles."""
        conn = self._get_conn()
        if team_role:
            cursor = conn.execute("""
                DELETE FROM audit_team
                WHERE audit_id = ? AND user_id = ? AND team_role = ?
            """, (audit_id, user_id, team_role))
        else:
            cursor = conn.execute("""
                DELETE FROM audit_team
                WHERE audit_id = ? AND user_id = ?
            """, (audit_id, user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def is_auditor_on_audit(self, user_id: int, audit_id: int) -> bool:
        """Check if a user is assigned as auditor on an audit."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT 1 FROM audit_team
            WHERE audit_id = ? AND user_id = ? AND team_role = 'auditor'
        """, (audit_id, user_id)).fetchone()
        conn.close()
        return row is not None

    def is_reviewer_on_audit(self, user_id: int, audit_id: int) -> bool:
        """Check if a user is assigned as reviewer on an audit."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT 1 FROM audit_team
            WHERE audit_id = ? AND user_id = ? AND team_role = 'reviewer'
        """, (audit_id, user_id)).fetchone()
        conn.close()
        return row is not None

    def is_team_member_on_audit(self, user_id: int, audit_id: int) -> bool:
        """Check if a user is assigned as either auditor or reviewer on an audit."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT 1 FROM audit_team
            WHERE audit_id = ? AND user_id = ?
        """, (audit_id, user_id)).fetchone()
        conn.close()
        return row is not None

    def get_audits_for_user_role(self, user_id: int, user_role: str, is_admin: bool = False) -> List[Dict]:
        """Get audits based on user's global role.

        - Admins: see all audits
        - Auditors/Reviewers: see ALL audits (full visibility)
        - Viewers: see ONLY audits specifically assigned to them
        """
        if is_admin:
            return self.get_all_audits()

        if user_role in ('auditor', 'reviewer'):
            # Auditors and reviewers can view ALL audits
            return self.get_all_audits()

        # Viewers can only see audits they're explicitly assigned to
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT DISTINCT a.* FROM audits a
            JOIN audit_viewers av ON a.id = av.audit_id
            WHERE av.viewer_user_id = ?
            ORDER BY a.title
        """, (user_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_team_roles_on_audit(self, user_id: int, audit_id: int) -> List[str]:
        """Get all team roles a user has on an audit (can be both auditor and reviewer)."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT team_role FROM audit_team
            WHERE audit_id = ? AND user_id = ?
        """, (audit_id, user_id)).fetchall()
        conn.close()
        return [row['team_role'] for row in rows]

    # ==================== WORKFLOW QUERIES ====================

    def get_records_by_status(self, record_type: str, audit_id: int,
                             status: str) -> List[Dict]:
        """Get all records of a type with a specific status."""
        table = 'risks' if record_type == 'risk' else 'issues'
        conn = self._get_conn()
        rows = conn.execute(f"""
            SELECT * FROM {table}
            WHERE audit_id = ? AND record_status = ?
            ORDER BY id
        """, (audit_id, status)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_records_in_review(self, reviewer_id: int) -> Dict[str, List[Dict]]:
        """Get all records in review for a specific reviewer."""
        conn = self._get_conn()

        risks = conn.execute("""
            SELECT r.*, a.title as audit_title
            FROM risks r
            JOIN audits a ON r.audit_id = a.id
            WHERE a.reviewer_id = ? AND r.record_status = 'in_review'
            ORDER BY r.audit_id, r.id
        """, (reviewer_id,)).fetchall()

        issues = conn.execute("""
            SELECT i.*, a.title as audit_title
            FROM issues i
            JOIN audits a ON i.audit_id = a.id
            WHERE a.reviewer_id = ? AND i.record_status = 'in_review'
            ORDER BY i.audit_id, i.id
        """, (reviewer_id,)).fetchall()

        conn.close()
        return {
            'risks': [dict(row) for row in risks],
            'issues': [dict(row) for row in issues]
        }

    def get_records_in_admin_hold(self) -> Dict[str, List[Dict]]:
        """Get all records currently in admin hold."""
        conn = self._get_conn()

        risks = conn.execute("""
            SELECT r.*, a.title as audit_title,
                   u.name as locked_by_name
            FROM risks r
            JOIN audits a ON r.audit_id = a.id
            LEFT JOIN users u ON r.admin_locked_by = u.id
            WHERE r.record_status = 'admin_hold'
            ORDER BY r.admin_locked_at DESC
        """).fetchall()

        issues = conn.execute("""
            SELECT i.*, a.title as audit_title,
                   u.name as locked_by_name
            FROM issues i
            JOIN audits a ON i.audit_id = a.id
            LEFT JOIN users u ON i.admin_locked_by = u.id
            WHERE i.record_status = 'admin_hold'
            ORDER BY i.admin_locked_at DESC
        """).fetchall()

        conn.close()
        return {
            'risks': [dict(row) for row in risks],
            'issues': [dict(row) for row in issues]
        }

    def get_workflow_summary(self, audit_id: int) -> Dict:
        """Get a summary of workflow status for an audit."""
        conn = self._get_conn()

        risk_summary = conn.execute("""
            SELECT record_status, COUNT(*) as count
            FROM risks WHERE audit_id = ?
            GROUP BY record_status
        """, (audit_id,)).fetchall()

        issue_summary = conn.execute("""
            SELECT record_status, COUNT(*) as count
            FROM issues WHERE audit_id = ?
            GROUP BY record_status
        """, (audit_id,)).fetchall()

        conn.close()

        return {
            'risks': {row['record_status'] or 'draft': row['count'] for row in risk_summary},
            'issues': {row['record_status'] or 'draft': row['count'] for row in issue_summary}
        }

    def get_all_records_by_status(self, status: str) -> List[Dict]:
        """Get all records with a specific status across all audits."""
        conn = self._get_conn()

        risks = conn.execute("""
            SELECT r.*, a.title as audit_title,
                   u.name as signed_off_by_name,
                   'risk' as record_type
            FROM risks r
            JOIN audits a ON r.audit_id = a.id
            LEFT JOIN users u ON r.signed_off_by = u.id
            WHERE r.record_status = ?
            ORDER BY r.signed_off_at DESC
        """, (status,)).fetchall()

        issues = conn.execute("""
            SELECT i.*, a.title as audit_title,
                   u.name as signed_off_by_name,
                   'issue' as record_type
            FROM issues i
            JOIN audits a ON i.audit_id = a.id
            LEFT JOIN users u ON i.signed_off_by = u.id
            WHERE i.record_status = ?
            ORDER BY i.signed_off_at DESC
        """, (status,)).fetchall()

        conn.close()

        return [dict(row) for row in risks] + [dict(row) for row in issues]


# Singleton instance for easy import
_db_instance = None

def get_db(db_path: Optional[str] = None) -> RACMDatabase:
    """Get or create the database instance."""
    global _db_instance
    if _db_instance is None or db_path:
        _db_instance = RACMDatabase(db_path)
    return _db_instance
