# Test Design Document

## Test Categories

1. Permission Tests
2. State Transition Tests
3. Data Segregation Tests
4. Negative Tests
5. Edge Case Tests
6. API Security Tests

---

## 1. Permission Tests

### 1.1 Record Edit Rights by Status

| Test ID | Record Status | User Role | User Assignment | Action | Expected Result |
|---------|---------------|-----------|-----------------|--------|-----------------|
| P001 | draft | auditor | assigned to audit | edit | ✅ Success |
| P002 | draft | auditor | NOT assigned | edit | ❌ 403 Forbidden |
| P003 | draft | reviewer | assigned to audit | edit | ❌ 403 Forbidden |
| P004 | draft | admin | any | edit | ❌ 403 Forbidden (view only) |
| P005 | draft | viewer | has access | edit | ❌ 403 Forbidden |
| P006 | in_review | auditor | assigned | edit | ❌ 403 Forbidden |
| P007 | in_review | reviewer | assigned | edit | ✅ Success |
| P008 | in_review | reviewer | NOT assigned | edit | ❌ 403 Forbidden |
| P009 | admin_hold | auditor | assigned | edit | ❌ 403 Forbidden |
| P010 | admin_hold | reviewer | assigned | edit | ❌ 403 Forbidden |
| P011 | admin_hold | admin | any | edit | ❌ 403 Forbidden (view only) |
| P012 | signed_off | auditor | assigned | edit | ❌ 403 Forbidden |
| P013 | signed_off | reviewer | assigned | edit | ❌ 403 Forbidden |
| P014 | signed_off | admin | any | edit | ❌ 403 Forbidden |

### 1.2 State Transition Permissions

| Test ID | Transition | User Role | Expected |
|---------|------------|-----------|----------|
| P015 | draft → in_review | auditor (assigned) | ✅ Success |
| P016 | draft → in_review | auditor (not assigned) | ❌ 403 |
| P017 | draft → in_review | reviewer | ❌ 403 |
| P018 | draft → in_review | admin | ❌ 403 |
| P019 | in_review → draft | reviewer (assigned) | ✅ Success |
| P020 | in_review → draft | reviewer (not assigned) | ❌ 403 |
| P021 | in_review → draft | auditor | ❌ 403 |
| P022 | in_review → signed_off | reviewer (assigned) | ✅ Success |
| P023 | in_review → signed_off | reviewer (not assigned) | ❌ 403 |
| P024 | in_review → signed_off | auditor | ❌ 403 |
| P025 | any → admin_hold | admin | ✅ Success |
| P026 | any → admin_hold | auditor | ❌ 403 |
| P027 | any → admin_hold | reviewer | ❌ 403 |
| P028 | admin_hold → draft | admin | ✅ Success |
| P029 | admin_hold → draft | auditor | ❌ 403 |
| P030 | signed_off → draft | admin | ✅ Success |
| P031 | signed_off → draft | auditor | ❌ 403 |
| P032 | signed_off → draft | reviewer | ❌ 403 |

### 1.3 Record Operations

| Test ID | Operation | User Role | Condition | Expected |
|---------|-----------|-----------|-----------|----------|
| P033 | create risk | auditor | own audit | ✅ Success |
| P034 | create risk | auditor | not own audit | ❌ 403 |
| P035 | create risk | reviewer | any | ❌ 403 |
| P036 | create risk | viewer | any | ❌ 403 |
| P037 | delete risk | admin | any | ✅ Success |
| P038 | delete risk | auditor | own audit | ❌ 403 |
| P039 | delete risk | reviewer | any | ❌ 403 |
| P040 | view risk | auditor | own audit | ✅ Success |
| P041 | view risk | reviewer | assigned audit | ✅ Success |
| P042 | view risk | viewer | shared audit | ✅ Success |
| P043 | view risk | viewer | not shared | ❌ 403 |

### 1.4 Viewer Management

| Test ID | Action | User Role | Condition | Expected |
|---------|--------|-----------|-----------|----------|
| P044 | add viewer | auditor | own audit | ✅ Success |
| P045 | add viewer | auditor | not own audit | ❌ 403 |
| P046 | add viewer | reviewer | assigned audit | ✅ Success |
| P047 | add viewer | admin | any audit | ✅ Success |
| P048 | add viewer | viewer | any | ❌ 403 |
| P049 | remove viewer | auditor | own audit | ✅ Success |
| P050 | remove viewer | admin | any | ✅ Success |
| P051 | list viewers | auditor | own audit | ✅ Success |
| P052 | list viewers | viewer | any | ❌ 403 |

---

## 2. State Transition Tests

### 2.1 Happy Path - Full Workflow

```
Test ST001: Complete workflow draft → in_review → signed_off

Setup:
  - Create audit with auditor1 and reviewer1
  - auditor1 creates risk R001

Steps:
  1. Verify R001.record_status = 'draft'
  2. Verify R001.current_owner_role = 'auditor'
  3. auditor1 edits R001 → Success
  4. auditor1 submits R001 for review
  5. Verify R001.record_status = 'in_review'
  6. Verify R001.current_owner_role = 'reviewer'
  7. Verify auditor1 cannot edit R001 → 403
  8. reviewer1 edits R001 → Success
  9. reviewer1 signs off R001
  10. Verify R001.record_status = 'signed_off'
  11. Verify R001.current_owner_role = 'none'
  12. Verify R001.signed_off_by = reviewer1.id
  13. Verify R001.signed_off_at is set
  14. Verify nobody can edit R001

Expected: All steps pass
```

### 2.2 Return Flow

```
Test ST002: Return to auditor flow

Setup:
  - Audit with auditor1, reviewer1
  - R002 in 'in_review' status

Steps:
  1. reviewer1 returns R002 with notes "Needs more detail"
  2. Verify R002.record_status = 'draft'
  3. Verify R002.current_owner_role = 'auditor'
  4. Verify reviewer1 cannot edit R002
  5. Verify auditor1 can edit R002
  6. auditor1 resubmits R002
  7. Verify R002.record_status = 'in_review'
  8. Verify reviewer1 can edit again

Expected: All steps pass
```

### 2.3 Admin Lock Flow

```
Test ST003: Admin lock and unlock

Setup:
  - R003 in 'in_review' status

Steps:
  1. admin locks R003 with reason "Audit committee review"
  2. Verify R003.record_status = 'admin_hold'
  3. Verify R003.admin_lock_reason = "Audit committee review"
  4. Verify auditor1 cannot edit
  5. Verify reviewer1 cannot edit
  6. admin unlocks R003, return_to = 'in_review'
  7. Verify R003.record_status = 'in_review'
  8. Verify reviewer1 can now edit

Expected: All steps pass
```

### 2.4 Admin Unlock Signed-Off

```
Test ST004: Unlock signed-off record

Setup:
  - R004 in 'signed_off' status

Steps:
  1. admin unlocks R004 with reason "Material error found"
  2. Verify confirmation "UNLOCK SIGNED OFF" required
  3. Verify R004.record_status = 'draft' (or in_review)
  4. Verify R004.signed_off_by = NULL
  5. Verify R004.signed_off_at = NULL
  6. Verify state_history entry created with full details

Expected: All steps pass
```

### 2.5 State History Tracking

```
Test ST005: Verify audit trail

Setup:
  - Create and process R005 through full workflow

Steps:
  1. Create R005 → history entry 'create'
  2. Submit for review → history entry 'submit_for_review'
  3. Return to auditor → history entry 'return_to_auditor'
  4. Resubmit → history entry 'submit_for_review'
  5. Sign off → history entry 'sign_off'
  6. Query history for R005
  7. Verify 5 entries with correct actions, users, timestamps

Expected: Complete audit trail exists
```

---

## 3. Data Segregation Tests

### 3.1 Auditor Segregation

```
Test DS001: Auditors cannot see each other's audits

Setup:
  - auditor1 assigned to Audit A
  - auditor2 assigned to Audit B

Steps:
  1. Login as auditor1
  2. GET /api/audits → Should only see Audit A
  3. GET /api/audits/{B}/risks → Should return 403
  4. Login as auditor2
  5. GET /api/audits → Should only see Audit B
  6. GET /api/audits/{A}/risks → Should return 403

Expected: Complete isolation between auditors
```

### 3.2 Viewer Access Control

```
Test DS002: Viewer can only see shared audits

Setup:
  - Audit A, Audit B exist
  - viewer1 has no access initially

Steps:
  1. Login as viewer1
  2. GET /api/audits → Should return empty
  3. Admin adds viewer1 to Audit A
  4. GET /api/audits → Should return only Audit A
  5. GET /api/audits/{A}/risks → Should succeed
  6. GET /api/audits/{B}/risks → Should return 403

Expected: Viewer sees exactly what's shared
```

### 3.3 Cross-Audit Record Access

```
Test DS003: Cannot access records from unauthorized audit

Setup:
  - auditor1 owns Audit A with risk R-A1
  - auditor2 owns Audit B with risk R-B1

Steps:
  1. Login as auditor1
  2. GET /api/risks/R-A1 → Success
  3. GET /api/risks/R-B1 → 403 Forbidden
  4. PUT /api/risks/R-B1 → 403 Forbidden

Expected: Audit boundaries enforced
```

---

## 4. Negative Tests

### 4.1 Invalid State Transitions

| Test ID | Current Status | Attempted Action | Expected |
|---------|----------------|------------------|----------|
| N001 | in_review | submit_for_review | 400 Bad Request |
| N002 | signed_off | submit_for_review | 400 Bad Request |
| N003 | draft | sign_off | 400 Bad Request |
| N004 | signed_off | sign_off | 400 Bad Request |
| N005 | draft | return_to_auditor | 400 Bad Request |
| N006 | admin_hold | sign_off | 400 Bad Request |
| N007 | admin_hold | admin_lock | 400 Bad Request |

### 4.2 Missing Required Fields

| Test ID | Action | Missing Field | Expected |
|---------|--------|---------------|----------|
| N008 | return_to_auditor | notes | 400 Bad Request |
| N009 | admin_lock | reason | 400 Bad Request |
| N010 | admin_unlock | reason | 400 Bad Request |
| N011 | admin_unlock | return_to | 400 Bad Request |
| N012 | admin_unlock_signoff | confirmation | 400 Bad Request |
| N013 | sign_off | confirmation | 400 Bad Request |

### 4.3 Invalid Confirmation Text

| Test ID | Action | Provided | Required | Expected |
|---------|--------|----------|----------|----------|
| N014 | sign_off | "sign off" | "SIGN OFF" | 400 Bad Request |
| N015 | sign_off | "" | "SIGN OFF" | 400 Bad Request |
| N016 | unlock_signoff | "unlock" | "UNLOCK SIGNED OFF" | 400 Bad Request |

### 4.4 Non-Existent Resources

| Test ID | Action | Resource | Expected |
|---------|--------|----------|----------|
| N017 | GET | /api/risks/NONEXISTENT | 404 Not Found |
| N018 | PUT | /api/risks/NONEXISTENT | 404 Not Found |
| N019 | submit_for_review | non-existent ID | 404 Not Found |
| N020 | add_viewer | non-existent user | 400 Bad Request |

---

## 5. Edge Case Tests

### 5.1 Concurrent Access

```
Test EC001: Concurrent edit attempt

Setup:
  - R001 in draft status
  - auditor1 assigned

Simulation:
  1. auditor1 session A loads R001 for editing
  2. auditor1 session B loads R001 for editing
  3. Session A submits edit → Success
  4. Session B submits edit → Should succeed (optimistic) OR
     conflict detected (pessimistic)

Note: For SQLite, last write wins. Document behavior.
```

```
Test EC002: Submit while reviewer is acting

Setup:
  - R002 in in_review status

Simulation:
  1. Reviewer loads R002
  2. Admin locks R002
  3. Reviewer tries to sign off → 403 (status changed)

Expected: Stale state detected, action rejected
```

### 5.2 Reassignment Scenarios

```
Test EC003: Auditor reassignment with drafts

Setup:
  - Audit A assigned to auditor1
  - R001, R002 in draft status

Steps:
  1. Admin reassigns Audit A to auditor2
  2. Verify auditor1 can no longer edit R001, R002
  3. Verify auditor2 CAN edit R001, R002
  4. Verify state_history records reassignment

Expected: Smooth handover with audit trail
```

```
Test EC004: Reviewer reassignment during review

Setup:
  - Audit A reviewer = reviewer1
  - R003 in in_review status

Steps:
  1. Admin reassigns reviewer to reviewer2
  2. Verify reviewer1 can no longer sign off
  3. Verify reviewer2 CAN sign off
  4. reviewer2 signs off successfully

Expected: New reviewer inherits in-progress reviews
```

### 5.3 User Deletion

```
Test EC005: Delete user with viewer access

Setup:
  - viewer1 has access to Audit A

Steps:
  1. Admin deletes viewer1
  2. Verify viewer1 cannot login
  3. Verify Audit A still accessible to others
  4. Verify audit_viewers record shows deleted user gracefully

Expected: Clean deletion, no orphaned data
```

```
Test EC006: Delete auditor with records

Setup:
  - auditor1 has created records in Audit A

Steps:
  1. Attempt to delete auditor1 → Should fail or warn
  2. Reassign Audit A to auditor2 first
  3. Then delete auditor1
  4. Verify records still reference created_by (historical)

Expected: Cannot delete user with active assignments
```

### 5.4 Audit Deletion

```
Test EC007: Delete audit with records

Setup:
  - Audit A has 5 risks in various states

Steps:
  1. Admin attempts DELETE /api/audits/{A}
  2. Should soft-delete (archive) not hard delete
  3. Verify audit status = 'archived'
  4. Verify records still exist but hidden from normal queries
  5. Verify state_history preserved

Expected: Soft delete preserves data integrity
```

---

## 6. API Security Tests

### 6.1 Authentication Tests

| Test ID | Endpoint | Auth | Expected |
|---------|----------|------|----------|
| API001 | GET /api/audits | None | 401 |
| API002 | GET /api/risks | None | 401 |
| API003 | POST /api/risks | None | 401 |
| API004 | PUT /api/risks/1 | None | 401 |
| API005 | DELETE /api/risks/1 | None | 401 |
| API006 | POST /api/records/risk/1/submit-for-review | None | 401 |
| API007 | GET /api/admin/users | None | 401 |
| API008 | POST /api/admin/records/risk/1/lock | None | 401 |

### 6.2 Authorization Tests

| Test ID | Endpoint | User | Expected |
|---------|----------|------|----------|
| API009 | GET /api/admin/users | auditor | 403 |
| API010 | POST /api/admin/users | reviewer | 403 |
| API011 | POST /api/admin/records/risk/1/lock | auditor | 403 |
| API012 | DELETE /api/risks/1 | auditor | 403 |
| API013 | POST /api/audits | reviewer | 403 |

### 6.3 CSRF Protection

```
Test API014: CSRF token validation

Steps:
  1. Login and get session
  2. Attempt POST without CSRF token
  3. Should fail (if CSRF enabled)

Note: Check if Flask-WTF or similar is in use
```

### 6.4 Input Validation

| Test ID | Endpoint | Invalid Input | Expected |
|---------|----------|---------------|----------|
| API015 | POST /api/risks | XSS in risk_id | Sanitized/Rejected |
| API016 | PUT /api/risks/1 | SQL injection | Sanitized/Rejected |
| API017 | POST /api/admin/records/risk/1/lock | reason > 10000 chars | 400 |

---

## 7. Test Execution Plan

### Phase 1: Unit Tests (Automated)
- Permission functions
- State transition validation
- Database methods

### Phase 2: Integration Tests (Automated)
- API endpoints with test client
- Full workflows

### Phase 3: Manual Testing
- UI permission checks
- Modal confirmations
- Admin console functions

### Phase 4: Security Testing
- Direct API access attempts
- Session manipulation attempts
- Input fuzzing

---

## 8. Test Data Setup

```python
def setup_test_data():
    # Users
    users = [
        {'email': 'auditor1@test.com', 'name': 'Alice Auditor', 'role': 'auditor'},
        {'email': 'auditor2@test.com', 'name': 'Bob Auditor', 'role': 'auditor'},
        {'email': 'reviewer1@test.com', 'name': 'Rachel Reviewer', 'role': 'reviewer'},
        {'email': 'reviewer2@test.com', 'name': 'Richard Reviewer', 'role': 'reviewer'},
        {'email': 'admin@test.com', 'name': 'Adam Admin', 'role': 'admin'},
        {'email': 'viewer1@test.com', 'name': 'Victor Viewer', 'role': 'viewer'},
    ]

    # Audits
    audits = [
        {'title': 'Test Audit A', 'auditor': 'auditor1', 'reviewer': 'reviewer1'},
        {'title': 'Test Audit B', 'auditor': 'auditor2', 'reviewer': 'reviewer2'},
    ]

    # Records in various states for testing
    risks = [
        {'audit': 'A', 'status': 'draft', 'risk_id': 'R-DRAFT-001'},
        {'audit': 'A', 'status': 'in_review', 'risk_id': 'R-REVIEW-001'},
        {'audit': 'A', 'status': 'admin_hold', 'risk_id': 'R-HOLD-001'},
        {'audit': 'A', 'status': 'signed_off', 'risk_id': 'R-SIGNED-001'},
    ]
```

---

## 9. Expected Test Results Summary

| Category | Total Tests | Must Pass |
|----------|-------------|-----------|
| Permission Tests | 52 | 52 |
| State Transition Tests | 5 scenarios | 5 |
| Data Segregation Tests | 3 scenarios | 3 |
| Negative Tests | 20 | 20 |
| Edge Case Tests | 7 scenarios | 7 |
| API Security Tests | 17 | 17 |
| **Total** | **~100** | **100%** |
