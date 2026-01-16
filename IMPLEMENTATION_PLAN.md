# User Access Control & Record Workflow Implementation Plan

## Overview

This document details the implementation plan for adding role-based permissions and record-level workflow management to SmartPapers.

---

## 1. Database Migrations

### 1.1 Modify `users` Table

```sql
-- Add role column to users
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer'
  CHECK (role IN ('auditor', 'reviewer', 'admin', 'viewer'));

-- Migrate existing data: is_admin=1 becomes role='admin'
UPDATE users SET role = 'admin' WHERE is_admin = 1;
UPDATE users SET role = 'auditor' WHERE is_admin = 0 AND role IS NULL;
```

### 1.2 Modify `audits` Table

```sql
-- Add auditor and reviewer assignment columns
ALTER TABLE audits ADD COLUMN auditor_id INTEGER REFERENCES users(id);
ALTER TABLE audits ADD COLUMN reviewer_id INTEGER REFERENCES users(id);
ALTER TABLE audits ADD COLUMN created_by INTEGER REFERENCES users(id);

-- Create indexes
CREATE INDEX idx_audits_auditor ON audits(auditor_id);
CREATE INDEX idx_audits_reviewer ON audits(reviewer_id);
```

### 1.3 Modify `risks` Table (RACM Records)

```sql
-- Add workflow state management columns
ALTER TABLE risks ADD COLUMN record_status TEXT DEFAULT 'draft'
  CHECK (record_status IN ('draft', 'in_review', 'admin_hold', 'signed_off'));
ALTER TABLE risks ADD COLUMN current_owner_role TEXT DEFAULT 'auditor'
  CHECK (current_owner_role IN ('auditor', 'reviewer', 'none'));

-- Admin lock tracking
ALTER TABLE risks ADD COLUMN admin_lock_reason TEXT;
ALTER TABLE risks ADD COLUMN admin_locked_by INTEGER REFERENCES users(id);
ALTER TABLE risks ADD COLUMN admin_locked_at TIMESTAMP;

-- Sign-off tracking
ALTER TABLE risks ADD COLUMN signed_off_by INTEGER REFERENCES users(id);
ALTER TABLE risks ADD COLUMN signed_off_at TIMESTAMP;

-- Audit trail
ALTER TABLE risks ADD COLUMN created_by INTEGER REFERENCES users(id);
ALTER TABLE risks ADD COLUMN updated_by INTEGER REFERENCES users(id);

-- Create indexes
CREATE INDEX idx_risks_record_status ON risks(record_status);
CREATE INDEX idx_risks_owner_role ON risks(current_owner_role);
```

### 1.4 Modify `issues` Table (Issue Log Records)

```sql
-- Add workflow state management columns (same as risks)
ALTER TABLE issues ADD COLUMN record_status TEXT DEFAULT 'draft'
  CHECK (record_status IN ('draft', 'in_review', 'admin_hold', 'signed_off'));
ALTER TABLE issues ADD COLUMN current_owner_role TEXT DEFAULT 'auditor'
  CHECK (current_owner_role IN ('auditor', 'reviewer', 'none'));

-- Admin lock tracking
ALTER TABLE issues ADD COLUMN admin_lock_reason TEXT;
ALTER TABLE issues ADD COLUMN admin_locked_by INTEGER REFERENCES users(id);
ALTER TABLE issues ADD COLUMN admin_locked_at TIMESTAMP;

-- Sign-off tracking
ALTER TABLE issues ADD COLUMN signed_off_by INTEGER REFERENCES users(id);
ALTER TABLE issues ADD COLUMN signed_off_at TIMESTAMP;

-- Audit trail
ALTER TABLE issues ADD COLUMN created_by INTEGER REFERENCES users(id);
ALTER TABLE issues ADD COLUMN updated_by INTEGER REFERENCES users(id);

-- Create indexes
CREATE INDEX idx_issues_record_status ON issues(record_status);
CREATE INDEX idx_issues_owner_role ON issues(current_owner_role);
```

### 1.5 New Table: `record_state_history`

```sql
CREATE TABLE record_state_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  record_type TEXT NOT NULL CHECK (record_type IN ('risk', 'issue')),
  record_id INTEGER NOT NULL,
  from_status TEXT,
  to_status TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN (
    'create',
    'submit_for_review',
    'return_to_auditor',
    'sign_off',
    'admin_lock',
    'admin_unlock',
    'admin_unlock_signoff'
  )),
  performed_by INTEGER REFERENCES users(id),
  performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  notes TEXT,
  reason TEXT
);

CREATE INDEX idx_state_history_record ON record_state_history(record_type, record_id);
CREATE INDEX idx_state_history_action ON record_state_history(action);
CREATE INDEX idx_state_history_user ON record_state_history(performed_by);
CREATE INDEX idx_state_history_date ON record_state_history(performed_at);
```

### 1.6 New Table: `audit_viewers`

```sql
CREATE TABLE audit_viewers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  viewer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  granted_by INTEGER REFERENCES users(id),
  granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(audit_id, viewer_user_id)
);

CREATE INDEX idx_audit_viewers_audit ON audit_viewers(audit_id);
CREATE INDEX idx_audit_viewers_user ON audit_viewers(viewer_user_id);
```

---

## 2. Permission System Design

### 2.1 Role Hierarchy

```
admin (level 1)    - System administration, override capabilities
auditor (level 2)  - Creates and edits records, owns drafting
reviewer (level 3) - Reviews and signs off records
viewer (level 4)   - Read-only access to shared audits
```

### 2.2 Permission Check Functions

```python
# In auth.py - new functions

def can_view_audit(user, audit):
    """Check if user can view an audit."""
    if user['role'] == 'admin':
        return True
    if user['role'] == 'auditor' and audit['auditor_id'] == user['id']:
        return True
    if user['role'] == 'reviewer' and audit['reviewer_id'] == user['id']:
        return True
    if user['role'] == 'viewer':
        # Check audit_viewers table
        return db.is_viewer_of_audit(user['id'], audit['id'])
    return False

def can_edit_record(user, audit, record):
    """Check if user can edit a specific record based on its status."""
    if record['record_status'] in ('signed_off', 'admin_hold'):
        return False

    if record['record_status'] == 'draft':
        return (user['role'] == 'auditor' and
                audit['auditor_id'] == user['id'])

    if record['record_status'] == 'in_review':
        return (user['role'] == 'reviewer' and
                audit['reviewer_id'] == user['id'])

    return False

def can_transition_record(user, audit, record, action):
    """Check if user can perform a state transition."""
    transitions = {
        'submit_for_review': lambda: (
            record['record_status'] == 'draft' and
            user['role'] == 'auditor' and
            audit['auditor_id'] == user['id']
        ),
        'return_to_auditor': lambda: (
            record['record_status'] == 'in_review' and
            user['role'] == 'reviewer' and
            audit['reviewer_id'] == user['id']
        ),
        'sign_off': lambda: (
            record['record_status'] == 'in_review' and
            user['role'] == 'reviewer' and
            audit['reviewer_id'] == user['id']
        ),
        'admin_lock': lambda: (
            user['role'] == 'admin' and
            record['record_status'] != 'admin_hold'
        ),
        'admin_unlock': lambda: (
            user['role'] == 'admin' and
            record['record_status'] == 'admin_hold'
        ),
        'admin_unlock_signoff': lambda: (
            user['role'] == 'admin' and
            record['record_status'] == 'signed_off'
        ),
    }
    return transitions.get(action, lambda: False)()
```

### 2.3 Decorator Updates

```python
# New decorator for record-level permissions
def require_record_edit(record_type):
    """Decorator that checks if user can edit the specified record."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            record_id = kwargs.get('record_id') or kwargs.get('risk_id') or kwargs.get('issue_id')

            record = db.get_record(record_type, record_id)
            if not record:
                return jsonify({'error': 'Record not found'}), 404

            audit = db.get_audit(record['audit_id'])
            if not can_edit_record(user, audit, record):
                return jsonify({'error': 'Cannot edit record in current state'}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
```

---

## 3. API Endpoint Structure

### 3.1 State Transition Endpoints

```
POST /api/records/<type>/<id>/submit-for-review
  - Request: { "notes": "optional notes" }
  - Response: { "status": "ok", "record_status": "in_review" }
  - Errors: 403 if not auditor or not draft

POST /api/records/<type>/<id>/return-to-auditor
  - Request: { "notes": "required feedback" }
  - Response: { "status": "ok", "record_status": "draft" }
  - Errors: 403 if not reviewer or not in_review, 400 if no notes

POST /api/records/<type>/<id>/sign-off
  - Request: { "confirmation": "SIGN OFF" }
  - Response: { "status": "ok", "record_status": "signed_off" }
  - Errors: 403 if not reviewer, 400 if wrong confirmation

POST /api/admin/records/<type>/<id>/lock
  - Request: { "reason": "required reason" }
  - Response: { "status": "ok", "record_status": "admin_hold" }
  - Errors: 403 if not admin, 400 if no reason

POST /api/admin/records/<type>/<id>/unlock
  - Request: { "reason": "required", "return_to": "draft|in_review" }
  - Response: { "status": "ok", "record_status": "<return_to>" }
  - Errors: 403 if not admin, 400 if invalid return_to

POST /api/admin/records/<type>/<id>/unlock-signoff
  - Request: { "reason": "required", "return_to": "draft|in_review", "confirmation": "UNLOCK SIGNED OFF" }
  - Response: { "status": "ok", "record_status": "<return_to>" }
  - Errors: 403 if not admin, 400 if wrong confirmation
```

### 3.2 Viewer Management Endpoints

```
GET /api/audits/<id>/viewers
  - Response: [{ "user_id": 1, "name": "...", "email": "...", "granted_at": "..." }]

POST /api/audits/<id>/viewers
  - Request: { "user_id": 123 }
  - Response: { "status": "ok" }
  - Errors: 403 if not auditor/reviewer of audit or admin

DELETE /api/audits/<id>/viewers/<user_id>
  - Response: { "status": "ok" }
  - Errors: 403 if not auditor/reviewer of audit or admin
```

### 3.3 State History Endpoints

```
GET /api/records/<type>/<id>/history
  - Response: [{ "action": "...", "from_status": "...", "to_status": "...", "performed_by": {...}, "performed_at": "...", "notes": "..." }]

GET /api/admin/audit-log
  - Query params: ?from_date=&to_date=&user_id=&action=&record_type=
  - Response: [{ ... full state history entries ... }]
```

### 3.4 Modified Existing Endpoints

```
PUT /api/risks/<risk_id>
  - Add permission check: can_edit_record()
  - Add updated_by tracking

PUT /api/issues/<issue_id>
  - Add permission check: can_edit_record()
  - Add updated_by tracking

POST /api/risks
  - Add created_by tracking
  - Add state history entry for 'create'

POST /api/issues
  - Add created_by tracking
  - Add state history entry for 'create'
```

---

## 4. Frontend Components

### 4.1 Record Status Badge Component

```javascript
function getStatusBadge(record_status) {
  const badges = {
    'draft': { icon: '📝', text: 'Draft', class: 'badge-blue' },
    'in_review': { icon: '🔍', text: 'In Review', class: 'badge-amber' },
    'admin_hold': { icon: '⏸️', text: 'Admin Hold', class: 'badge-red' },
    'signed_off': { icon: '✅', text: 'Signed Off', class: 'badge-green' }
  };
  return badges[record_status] || badges['draft'];
}
```

### 4.2 Permission Helper (Client-side)

```javascript
function getRecordPermissions(user, audit, record) {
  const isAuditor = user.role === 'auditor' && audit.auditor_id === user.id;
  const isReviewer = user.role === 'reviewer' && audit.reviewer_id === user.id;
  const isAdmin = user.role === 'admin';

  return {
    canView: true, // If they can see it, they can view it
    canEdit:
      (record.record_status === 'draft' && isAuditor) ||
      (record.record_status === 'in_review' && isReviewer),
    canSubmitForReview: record.record_status === 'draft' && isAuditor,
    canReturnToAuditor: record.record_status === 'in_review' && isReviewer,
    canSignOff: record.record_status === 'in_review' && isReviewer,
    canAdminLock: isAdmin && record.record_status !== 'admin_hold',
    canAdminUnlock: isAdmin && record.record_status === 'admin_hold',
    canAdminUnlockSignoff: isAdmin && record.record_status === 'signed_off'
  };
}
```

### 4.3 Confirmation Modals Required

1. **Submit for Review Modal**
   - Warning about losing edit access
   - Optional notes field

2. **Return to Auditor Modal**
   - Required feedback field
   - Warning about losing edit access

3. **Sign Off Modal**
   - Strong warning (cannot be undone)
   - Type "SIGN OFF" confirmation

4. **Admin Lock Modal**
   - Shows current status/owner
   - Required reason field

5. **Admin Unlock Modal**
   - Required reason
   - Radio: Return to Draft / In Review

6. **Admin Unlock Signed-Off Modal**
   - Strongest warning (audit trail integrity)
   - Required reason
   - Radio: Return to Draft / In Review
   - Type "UNLOCK SIGNED OFF" confirmation

### 4.4 RACM Grid Updates

- Add "Status" column showing record_status badge
- Add "Actions" column with conditional buttons
- Disable cell editing based on can_edit_record()
- Add row highlighting based on status

### 4.5 Admin Console Updates

New tabs/panels:
1. **Record Override Panel**
   - Filter by audit, status
   - Lock/unlock actions
   - Bulk operations

2. **Audit Trail Log**
   - All state transitions
   - Filterable by date, user, action
   - Export to CSV

---

## 5. File Structure for New Code

```
racm-smartp-test/
├── auth.py                    # Add new permission functions
├── database.py                # Add new DB methods
├── app.py                     # Add new endpoints
├── migrations/
│   └── 001_workflow_schema.py # New migration script
├── templates/
│   ├── index.html             # Update RACM grid
│   └── admin/
│       └── dashboard.html     # Add new tabs
└── static/
    └── js/
        └── permissions.js     # Client-side permission helpers
```

---

## 6. Migration Strategy

### Step 1: Schema Migration
Run database migrations to add new columns and tables.

### Step 2: Data Migration
- Set all existing risks/issues to `record_status='draft'`
- Set `current_owner_role='auditor'` for all
- Migrate `is_admin` users to `role='admin'`
- Set non-admin users to `role='auditor'` (default)

### Step 3: API Updates
- Add permission checks to existing endpoints
- Add new state transition endpoints

### Step 4: Frontend Updates
- Add status badges
- Add action buttons
- Add confirmation modals

### Step 5: Admin Console
- Add record override panel
- Add audit trail viewer

---

## 7. Test Accounts to Create

| Email | Password | Role | Name |
|-------|----------|------|------|
| auditor1@test.com | Test123! | auditor | Alice Auditor |
| auditor2@test.com | Test123! | auditor | Bob Auditor |
| reviewer1@test.com | Test123! | reviewer | Rachel Reviewer |
| reviewer2@test.com | Test123! | reviewer | Richard Reviewer |
| admin@test.com | Test123! | admin | Adam Admin |
| viewer1@test.com | Test123! | viewer | Victor Viewer |

---

## 8. Implementation Order

1. **Database migrations** (schema changes)
2. **Permission functions** in auth.py
3. **Database methods** for state transitions
4. **State transition API endpoints**
5. **Viewer management API endpoints**
6. **Modify existing CRUD endpoints** with permission checks
7. **Frontend status badges** and permission helpers
8. **Action buttons** with permission-based rendering
9. **Confirmation modals**
10. **Admin console** record override panel
11. **Audit trail** viewer
12. **Seed test accounts**
13. **Run tests**

---

## 9. Estimated Changes Summary

| Area | Files Modified | New Files |
|------|----------------|-----------|
| Database | database.py | migrations/001_workflow_schema.py |
| Auth | auth.py | - |
| API | app.py | - |
| Templates | index.html, admin/dashboard.html | - |
| Static | - | static/js/permissions.js |

Total: ~1500-2000 lines of new/modified code
