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

    def get_audits_as_spreadsheet(self) -> List[List]:
        """Get audits in spreadsheet format (array of arrays)."""
        audits = self.get_all_audits()
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

    def get_audits_as_kanban(self) -> Dict:
        """Get audits grouped by status for kanban view."""
        audits = self.get_all_audits()
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

    def save_flowchart(self, name: str, data: Dict, risk_id: Optional[str] = None) -> int:
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
            INSERT INTO flowcharts (name, data, risk_id, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                data = excluded.data,
                risk_id = excluded.risk_id,
                updated_at = CURRENT_TIMESTAMP
        """, (name, json.dumps(data), fk_risk_id))
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
        cursor = conn.execute("""
            INSERT INTO test_documents (risk_id, doc_type, content, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(risk_id, doc_type) DO UPDATE SET
                content = excluded.content,
                updated_at = CURRENT_TIMESTAMP
        """, (risk_id, doc_type, content))
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

        # Block dangerous keywords that could modify data
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'ATTACH',
            'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX'
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


# Singleton instance for easy import
_db_instance = None

def get_db(db_path: Optional[str] = None) -> RACMDatabase:
    """Get or create the database instance."""
    global _db_instance
    if _db_instance is None or db_path:
        _db_instance = RACMDatabase(db_path)
    return _db_instance
