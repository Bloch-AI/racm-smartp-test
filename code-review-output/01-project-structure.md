# Phase 1: Project Structure Review

**Review Date:** 2026-01-15
**Reviewer:** Claude Code Review Agent

## Executive Summary

SmartPapers is a Flask-based internal audit management application with AI assistance capabilities. The project implements a multi-audit system with Role-Based Access Control (RBAC), RACM (Risk Assessment and Control Matrix) management, Kanban task tracking, and an AI assistant powered by Claude.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Flask (Python) |
| Database | SQLite |
| AI Integration | Anthropic Claude API (claude-sonnet-4-20250514) |
| Vector Search | sqlite-vec + sentence-transformers |
| Authentication | Session-based with werkzeug password hashing |
| Frontend | Jinja2 templates, vanilla JavaScript |
| Document Processing | pdfplumber, python-docx, openpyxl |

## Project File Structure

```
racm-smartp-test/
├── app.py              # Main Flask application (~3200 lines)
├── database.py         # SQLite database layer (~1500+ lines)
├── auth.py             # Authentication decorators (237 lines)
├── seed_data.py        # Sample data generator (597 lines)
├── test_app.py         # Test suite (144 tests)
├── test_frontend.py    # Frontend test file (present but needs review)
├── .env                # Environment configuration
├── .gitignore          # Git ignore rules
├── templates/
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Workpapers/RACM view
│   ├── felix.html      # AI Assistant chat interface
│   ├── flowchart.html  # Drawflow process diagrams
│   ├── kanban.html     # Task management board
│   ├── audit_plan.html # Annual audit plan
│   ├── library.html    # Audit reference library
│   ├── login.html      # Authentication page
│   └── admin/
│       └── dashboard.html  # Admin control panel
├── static/
│   ├── css/
│   │   └── common.css  # Shared styles
│   ├── js/
│   │   └── utils.js    # JavaScript utilities
│   └── logo.png        # Application logo
├── uploads/            # User-uploaded attachments
├── library/            # Audit reference documents
└── racm_data.db        # SQLite database file (gitignored)
```

## Entry Points

| Entry Point | Purpose |
|-------------|---------|
| `app.py` | Main application, run with `flask run` or `python3 app.py` |
| `seed_data.py` | Run standalone to populate sample data |
| `test_app.py` | pytest test suite entry |

## Core Dependencies

### Required (Explicit in imports)
- Flask
- python-dotenv
- anthropic (Claude API client)
- werkzeug (password hashing, secure filename)
- sqlite3 (standard library)

### Optional (graceful degradation)
- pdfplumber (PDF text extraction)
- python-docx (Word document processing)
- openpyxl (Excel file processing)
- sentence-transformers (embedding generation)
- sqlite-vec (vector similarity search)

## Database Schema Overview

### Core Tables
- `risks` - RACM rows (risks/controls)
- `issues` - Issue log entries
- `tasks` - Kanban board items
- `audits` - Annual audit plan entries
- `flowcharts` - Process diagrams (Drawflow JSON)
- `test_documents` - Rich text testing documentation

### Attachment Tables
- `risk_attachments` - Files attached to RACM rows
- `issue_attachments` - Files attached to issues
- `audit_attachments` - Files attached to audits

### RBAC Tables
- `users` - User accounts
- `roles` - Role definitions (admin, auditor, reviewer, viewer)
- `audit_memberships` - User-audit-role assignments

### Library Tables
- `library_documents` - Reference document metadata
- `library_chunks` - Chunked content with embeddings

## Key Findings

### Strengths
1. **Well-structured RBAC** - Clean separation of authentication and authorization decorators
2. **Database migrations** - Idempotent schema migrations with proper ALTER TABLE handling
3. **Optional dependencies** - Graceful degradation when text extraction libraries unavailable
4. **Test coverage** - 144 tests covering database, API, and authentication

### Concerns
1. **Monolithic app.py** - Single 3200+ line file should be split into blueprints
2. **No requirements.txt** - Dependencies not formally declared
3. **No CI/CD configuration** - Missing GitHub Actions or similar
4. **No logging configuration** - Using print statements instead of proper logging

## Recommendations

1. **Split app.py into Flask Blueprints**:
   - `routes/auth.py` - Authentication routes
   - `routes/api.py` - REST API endpoints
   - `routes/admin.py` - Admin panel routes
   - `routes/felix.py` - AI assistant routes

2. **Add requirements.txt or pyproject.toml**:
   ```
   flask>=2.0
   python-dotenv
   anthropic
   werkzeug
   pdfplumber
   python-docx
   openpyxl
   sentence-transformers
   pytest
   ```

3. **Add proper logging** - Replace print statements with logging module

4. **Add Dockerfile** - For containerized deployment
