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

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            -- Risks and Controls (RACM rows)
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_id TEXT UNIQUE NOT NULL,
                risk_description TEXT,
                control_description TEXT,
                control_owner TEXT,
                frequency TEXT,
                status TEXT DEFAULT 'Not Tested',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Kanban Tasks
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

            -- Flowcharts (stores Drawflow JSON)
            CREATE TABLE IF NOT EXISTS flowcharts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                data JSON NOT NULL,
                risk_id INTEGER REFERENCES risks(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Index for common queries
            CREATE INDEX IF NOT EXISTS idx_risks_status ON risks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_risk ON tasks(risk_id);
            CREATE INDEX IF NOT EXISTS idx_flowcharts_risk ON flowcharts(risk_id);
        """)
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

    def create_risk(self, risk_id: str, risk_description: str = "",
                    control_description: str = "", control_owner: str = "",
                    frequency: str = "", status: str = "Not Tested") -> int:
        """Create a new risk/control. Returns the new ID."""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO risks (risk_id, risk_description, control_description,
                              control_owner, frequency, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (risk_id, risk_description, control_description, control_owner, frequency, status))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_risk(self, risk_id: str, **kwargs) -> bool:
        """Update a risk. Pass fields to update as kwargs."""
        allowed = {'risk_description', 'control_description', 'control_owner',
                   'frequency', 'status'}
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

    # ==================== AI QUERY HELPERS ====================

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute a raw SQL query (for AI-generated queries).
        READ-ONLY - only SELECT statements allowed."""
        if not sql.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries allowed")

        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_schema(self) -> str:
        """Return database schema for AI context."""
        return """
DATABASE SCHEMA:

TABLE risks (RACM - Risk and Control Matrix):
  - id: INTEGER PRIMARY KEY
  - risk_id: TEXT (e.g., 'R001', 'R002')
  - risk_description: TEXT
  - control_description: TEXT
  - control_owner: TEXT
  - frequency: TEXT (Daily, Weekly, Monthly, Quarterly, Ongoing)
  - status: TEXT (Effective, Needs Improvement, Ineffective, Not Tested)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE tasks (Kanban board items):
  - id: INTEGER PRIMARY KEY
  - title: TEXT
  - description: TEXT
  - priority: TEXT (low, medium, high)
  - assignee: TEXT
  - column_id: TEXT (planning, fieldwork, testing, review, complete)
  - risk_id: INTEGER (FK to risks.id)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

TABLE flowcharts (Process diagrams):
  - id: INTEGER PRIMARY KEY
  - name: TEXT (unique identifier)
  - data: JSON (Drawflow format)
  - risk_id: INTEGER (FK to risks.id)
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

RELATIONSHIPS:
  - tasks.risk_id -> risks.id (many tasks can link to one risk)
  - flowcharts.risk_id -> risks.id (flowchart can document a risk's control)
"""

    def get_full_context(self) -> Dict:
        """Get full database context for AI."""
        return {
            'schema': self.get_schema(),
            'risk_summary': self.get_risk_summary(),
            'task_summary': self.get_task_summary(),
            'flowchart_count': len(self.get_all_flowcharts()),
            'risks': self.get_all_risks(),
            'tasks': self.get_all_tasks(),
            'flowcharts': [{'name': f['name'], 'risk_id': f['risk_id']}
                          for f in self.get_all_flowcharts()]
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
        header = ['Risk ID', 'Risk Description', 'Control Description',
                  'Control Owner', 'Frequency', 'Status', 'Flowchart', 'Task']

        rows = [header]
        for r in risks:
            # Find linked flowchart and task
            conn = self._get_conn()
            fc = conn.execute("SELECT name FROM flowcharts WHERE risk_id = ?", (r['id'],)).fetchone()
            task = conn.execute("SELECT title FROM tasks WHERE risk_id = ?", (r['id'],)).fetchone()
            conn.close()

            rows.append([
                r['risk_id'],
                r['risk_description'] or '',
                r['control_description'] or '',
                r['control_owner'] or '',
                r['frequency'] or '',
                r['status'] or '',
                fc['name'] if fc else '',
                task['title'] if task else ''
            ])
        return rows

    def save_from_spreadsheet(self, data: List[List]):
        """Save risks from spreadsheet format (for backward compatibility)."""
        if not data or len(data) < 1:
            return

        # Skip header row
        for row in data[1:]:
            if len(row) >= 6 and row[0]:  # Must have risk_id at minimum
                risk_id = row[0]
                existing = self.get_risk(risk_id)

                if existing:
                    self.update_risk(
                        risk_id,
                        risk_description=row[1] if len(row) > 1 else '',
                        control_description=row[2] if len(row) > 2 else '',
                        control_owner=row[3] if len(row) > 3 else '',
                        frequency=row[4] if len(row) > 4 else '',
                        status=row[5] if len(row) > 5 else 'Not Tested'
                    )
                else:
                    self.create_risk(
                        risk_id=risk_id,
                        risk_description=row[1] if len(row) > 1 else '',
                        control_description=row[2] if len(row) > 2 else '',
                        control_owner=row[3] if len(row) > 3 else '',
                        frequency=row[4] if len(row) > 4 else '',
                        status=row[5] if len(row) > 5 else 'Not Tested'
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
