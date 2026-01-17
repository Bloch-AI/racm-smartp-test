"""
001: Initial database schema.

Creates all core tables for RACM audit toolkit.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Create initial database schema."""
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
        CREATE INDEX IF NOT EXISTS idx_attachments_category ON risk_attachments(category);

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
