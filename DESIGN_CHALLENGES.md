# Design Challenge Analysis

## Security Challenges

### 1. How could permission checks be bypassed?

**Risk:** Client-side permission checks without server validation.

**Mitigation:**
- ALL permission checks happen server-side in API endpoints
- Client-side checks are for UX only (hiding buttons)
- Every API endpoint validates permissions before any action
- Use decorators consistently: `@require_login`, `@require_audit_access`, `@require_record_edit`

**Implementation:**
```python
# Every PUT/POST endpoint must include:
@app.route('/api/risks/<risk_id>', methods=['PUT'])
@require_login
def update_risk(risk_id):
    user = get_current_user()
    risk = db.get_risk(risk_id)
    audit = db.get_audit(risk['audit_id'])

    # Server-side permission check - cannot be bypassed
    if not can_edit_record(user, audit, risk):
        return jsonify({'error': 'Cannot edit record in current state'}), 403

    # ... proceed with update
```

### 2. What if someone calls the API directly, bypassing the UI?

**Risk:** Direct API calls could bypass UI-enforced workflows.

**Mitigation:**
- API endpoints are the ONLY way to modify data
- UI permission checks mirror API checks exactly
- All state transitions require explicit API calls with validation
- No "hidden" endpoints or backdoors

**Test:** Use curl/Postman to attempt all operations without UI.

### 3. Could a user manipulate their session/claims?

**Risk:** Session tampering to gain elevated privileges.

**Mitigation:**
- Flask sessions are signed with SECRET_KEY
- User role is read from database on each request, not stored in session
- `get_current_user()` always fetches fresh from DB
- Session only stores user_id, all permissions derived from DB lookup

**Implementation:**
```python
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    # ALWAYS fetch from DB - never trust session for role/permissions
    user = db.get_user_by_id(user_id)
    return user
```

### 4. Are there any endpoints missing auth checks?

**Audit checklist for all endpoints:**
- [ ] `/api/risks/*` - needs `@require_login` + audit access check
- [ ] `/api/issues/*` - needs `@require_login` + audit access check
- [ ] `/api/audits/*` - needs `@require_login` + role-based access
- [ ] `/api/records/*/submit-for-review` - needs auditor check
- [ ] `/api/records/*/sign-off` - needs reviewer check
- [ ] `/api/admin/*` - needs `@require_admin`

**Mitigation:** Create test that iterates all `/api/*` routes and verifies they return 401 without auth.

---

## State Machine Challenges

### 5. What happens if two users act simultaneously on the same record?

**Scenario:** Auditor submits for review while reviewer is trying to return it.

**Risk:** Race condition could leave record in invalid state.

**Mitigation:**
- Use database transactions with row-level locking
- Check current status WITHIN the transaction before updating
- Return error if status changed since request was initiated

**Implementation:**
```python
def submit_for_review(record_id):
    with db._connection() as conn:
        # Lock the row
        record = conn.execute(
            "SELECT * FROM risks WHERE id = ? FOR UPDATE",
            (record_id,)
        ).fetchone()

        # Verify status hasn't changed
        if record['record_status'] != 'draft':
            return {'error': 'Record is no longer in draft status'}, 409

        # Proceed with update
        conn.execute(
            "UPDATE risks SET record_status = 'in_review' WHERE id = ?",
            (record_id,)
        )
```

**Note:** SQLite doesn't support `FOR UPDATE` but is single-writer, so we use immediate transactions:
```python
conn.execute("BEGIN IMMEDIATE")  # Exclusive lock for writes
```

### 6. Are there any states where a record could become "stuck"?

**Analysis:**

| Status | Can transition to | Risk of stuck? |
|--------|-------------------|----------------|
| draft | in_review | No - auditor can always submit |
| in_review | draft, signed_off | No - reviewer can return or sign off |
| admin_hold | draft, in_review | Yes - requires admin action |
| signed_off | draft, in_review | Yes - requires admin action |

**Potential stuck scenarios:**
1. Admin places hold and leaves organization
2. Signed-off record needs correction but admin unavailable

**Mitigation:**
- Multiple admins should exist in production
- Admin console shows records in admin_hold state
- Alerts/notifications for records stuck > X days (future enhancement)

### 7. Can a record ever end up in an invalid state?

**Invalid states to prevent:**
- `record_status = 'in_review'` but `current_owner_role = 'auditor'`
- `record_status = 'signed_off'` but `signed_off_by = NULL`
- `record_status = 'admin_hold'` but `admin_lock_reason = NULL`

**Mitigation:**
- State transition functions are atomic - update all related fields together
- Database constraints where possible
- Validation function to check state consistency

**Implementation:**
```python
def transition_to_signed_off(record_id, user_id):
    # Atomic update - all fields or nothing
    conn.execute("""
        UPDATE risks SET
            record_status = 'signed_off',
            current_owner_role = 'none',
            signed_off_by = ?,
            signed_off_at = CURRENT_TIMESTAMP,
            updated_by = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND record_status = 'in_review'
    """, (user_id, user_id, record_id))

    if conn.rowcount == 0:
        raise ValueError("Record was not in expected state")
```

### 8. What if the database transaction fails midway through a state change?

**Risk:** Partial update leaves inconsistent data.

**Mitigation:**
- All state changes in single transaction
- Use `conn.execute()` within context manager
- SQLite auto-rollback on exception

**Implementation:**
```python
def perform_state_transition(record_id, action, user_id, **kwargs):
    with db._connection() as conn:
        try:
            # 1. Update record status (atomic)
            update_record_status(conn, record_id, ...)

            # 2. Create history entry
            create_state_history(conn, record_id, action, ...)

            # Both succeed or both fail
            conn.commit()
        except Exception:
            conn.rollback()
            raise
```

---

## Edge Case Challenges

### 9. What if an auditor is removed from an audit while they have records in draft?

**Scenario:** Auditor A has 10 records in draft. Admin reassigns audit to Auditor B.

**Options:**
1. Block reassignment if records in draft
2. Auto-transition drafts to new auditor
3. Leave records with original auditor (orphaned)

**Recommendation:** Option 2 - Records belong to the audit, not the user.

**Implementation:**
- When `audits.auditor_id` changes, records remain in their current state
- New auditor inherits all draft records
- Add state history entry: "Auditor reassigned from X to Y"

### 10. What if a reviewer is reassigned while records are in review?

**Same approach as #9:**
- Records in `in_review` transfer to new reviewer
- New reviewer can sign off or return
- History entry tracks the reassignment

### 11. What if an admin deletes an audit with records in various states?

**Risk:** Cascade delete loses audit trail.

**Mitigation options:**
1. Soft delete (set audit.status = 'deleted')
2. Block delete if any records exist
3. Archive audit and records

**Recommendation:** Option 1 + 2 combined:
- Soft delete by default
- Hard delete only allowed if audit has no records
- Deleted audits hidden from UI but preserved in DB

**Implementation:**
```python
def delete_audit(audit_id):
    record_count = db.count_records_for_audit(audit_id)
    if record_count > 0:
        # Soft delete
        db.update_audit(audit_id, status='archived')
        return {'status': 'archived', 'message': 'Audit archived (has records)'}
    else:
        # Hard delete OK
        db.hard_delete_audit(audit_id)
        return {'status': 'deleted'}
```

### 12. What happens to viewer access if the granting user is deleted?

**Analysis:** `audit_viewers.granted_by` references deleted user.

**Mitigation:**
- `granted_by` can be NULL (user deleted)
- Access remains valid until explicitly revoked
- Viewer list shows "Granted by: (deleted user)"

**Implementation:**
```sql
-- Allow NULL for deleted users
ALTER TABLE audit_viewers
  ALTER COLUMN granted_by DROP NOT NULL;
```

---

## Additional Security Considerations

### 13. Audit Trail Integrity

**Risk:** Admin could delete state history to hide actions.

**Mitigation:**
- No DELETE endpoint for state_history
- Even admins cannot delete history entries
- Consider append-only table design

### 14. Sign-off Cannot Be Undone (Except by Admin)

**Enforcement:**
- Sign-off transition is one-way for auditors/reviewers
- Only `admin_unlock_signoff` can reverse
- Requires typed confirmation AND reason
- All unlock actions logged with full context

### 15. Password Security

**Current:** Using werkzeug's `pbkdf2:sha256`
**Status:** Adequate for now, consider bcrypt for future.

---

## Design Revisions Based on Challenges

### Revision 1: Add reassignment tracking
Add `previous_auditor_id` and `previous_reviewer_id` to state history when assignments change.

### Revision 2: Audit soft delete
Change `DELETE /api/audits/:id` to soft delete by default.

### Revision 3: State consistency validation
Add `validate_record_state()` function called after every transition.

### Revision 4: Transaction wrapper
Create `@atomic_transaction` decorator for state changes.

---

## Summary: Key Mitigations

| Challenge | Mitigation |
|-----------|------------|
| API bypass | Server-side checks on every endpoint |
| Session tampering | Fetch user from DB on each request |
| Race conditions | Database transactions with locking |
| Stuck records | Admin override capability + monitoring |
| Invalid states | Atomic updates + validation |
| Transaction failures | Single transaction + rollback |
| Reassignment | Records transfer with audit assignment |
| Audit deletion | Soft delete if records exist |
| Audit trail integrity | No delete capability for history |
