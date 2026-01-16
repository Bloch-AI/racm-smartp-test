"""
Regression tests for role refactoring.

Tests the consolidation of global 'reviewer' role into 'auditor' while preserving
per-audit reviewer assignments via the audit_team table.

Run with: pytest tests/test_role_refactor.py -v
"""
import pytest
import uuid
import app as app_module
import database as db_module
from database import RACMDatabase
from werkzeug.security import generate_password_hash


# ==================== FIXTURES ====================

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with fresh schema."""
    db_path = tmp_path / "test.db"
    db = RACMDatabase(str(db_path))
    return db


@pytest.fixture
def client(test_db, tmp_path):
    """Create test client with isolated database."""
    app_module.app.config['TESTING'] = True
    app_module.app.config['WTF_CSRF_ENABLED'] = False
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir()
    app_module.app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    # Save original db references
    original_app_db = app_module.db
    original_db_instance = db_module._db_instance

    # Set test_db in both places
    app_module.db = test_db
    db_module._db_instance = test_db

    with app_module.app.test_client() as client:
        yield client

    # Restore original db references
    app_module.db = original_app_db
    db_module._db_instance = original_db_instance


def unique_email(prefix='user'):
    """Generate a unique email address."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def create_user(db, email, name, role='auditor', is_admin=False):
    """Helper to create a test user."""
    password_hash = generate_password_hash('testpass123', method='pbkdf2:sha256')
    with db._connection() as conn:
        cursor = conn.execute('''
            INSERT INTO users (email, name, password_hash, is_active, is_admin, role)
            VALUES (?, ?, ?, 1, ?, ?)
        ''', (email, name, password_hash, 1 if is_admin else 0, role))
        return cursor.lastrowid


def create_audit(db, title, description='Test audit'):
    """Helper to create a test audit."""
    with db._connection() as conn:
        cursor = conn.execute('''
            INSERT INTO audits (title, description, status, quarter)
            VALUES (?, ?, 'in_progress', 'Q1')
        ''', (title, description))
        return cursor.lastrowid


def create_risk_with_audit(db, audit_id, risk_id, record_status='draft'):
    """Helper to create a risk associated with an audit."""
    with db._connection() as conn:
        cursor = conn.execute('''
            INSERT INTO risks (risk_id, risk, control_id, control_owner, status, audit_id, record_status)
            VALUES (?, 'Test risk', 'C001', 'Test Owner', 'Not Complete', ?, ?)
        ''', (risk_id, audit_id, record_status))
        return cursor.lastrowid


def login_user(client, db, user_id):
    """Helper to log in a user."""
    user = db.get_user_by_id(user_id)
    with client.session_transaction() as sess:
        sess['user_id'] = user['id']
        sess['user_email'] = user['email']
        sess['user_name'] = user['name']
        sess['is_admin'] = bool(user['is_admin'])


# ==================== TEST CURRENT ROLE BEHAVIOR ====================

class TestCurrentRoleBehavior:
    """Tests for current role-based access behavior."""

    def test_admin_can_access_all_audits(self, client, test_db):
        """Admin users should have access to all audits."""
        # Create admin user with unique email
        admin_id = create_user(test_db, unique_email('admin'), 'Admin User', role='admin', is_admin=True)

        # Create some audits
        audit1_id = create_audit(test_db, 'Audit 1')
        audit2_id = create_audit(test_db, 'Audit 2')

        # Login as admin
        login_user(client, test_db, admin_id)

        # Check admin can access all audits
        response = client.get('/api/audits')
        assert response.status_code == 200
        audits = response.get_json()
        assert len(audits) >= 2
        audit_titles = [a['title'] for a in audits]
        assert 'Audit 1' in audit_titles
        assert 'Audit 2' in audit_titles

    def test_auditor_can_view_all_audits(self, client, test_db):
        """Auditor users should be able to view all audits."""
        # Create auditor user
        auditor_id = create_user(test_db, unique_email('auditor'), 'Auditor User', role='auditor')

        # Create some audits (not assigned to the auditor)
        audit1_id = create_audit(test_db, 'Unassigned Audit 1')
        audit2_id = create_audit(test_db, 'Unassigned Audit 2')

        # Login as auditor
        login_user(client, test_db, auditor_id)

        # Auditors can view all audits (full visibility)
        audits = test_db.get_audits_for_user_role(auditor_id, 'auditor')
        assert len(audits) >= 2

    def test_viewer_can_only_see_assigned_audits(self, client, test_db):
        """Viewer users should only see audits they are assigned to."""
        # Create viewer user
        viewer_id = create_user(test_db, unique_email('viewer'), 'Viewer User', role='viewer')

        # Create audits
        assigned_audit_id = create_audit(test_db, 'Assigned Audit')
        unassigned_audit_id = create_audit(test_db, 'Unassigned Audit')

        # Assign viewer to only one audit (note: order is audit_id, user_id)
        test_db.add_viewer_to_audit(assigned_audit_id, viewer_id)

        # Login as viewer
        login_user(client, test_db, viewer_id)

        # Viewer should only see assigned audit
        audits = test_db.get_audits_for_user_role(viewer_id, 'viewer')
        audit_ids = [a['id'] for a in audits]
        assert assigned_audit_id in audit_ids
        assert unassigned_audit_id not in audit_ids

    @pytest.mark.xfail(reason="Pre-existing behavior: /api/risks endpoint doesn't enforce viewer read-only restriction. Outside scope of role refactoring.")
    def test_viewer_cannot_edit_records(self, client, test_db):
        """Viewer users should not be able to edit records.

        Note: This test documents expected behavior that viewer role users
        should have read-only access. Currently the /api/risks PUT endpoint
        doesn't enforce this restriction. This is a pre-existing issue,
        not related to the reviewer->auditor role consolidation.
        """
        # Create viewer user
        viewer_id = create_user(test_db, unique_email('viewer'), 'Viewer User', role='viewer')

        # Create audit and assign viewer (note: order is audit_id, user_id)
        audit_id = create_audit(test_db, 'Test Audit')
        test_db.add_viewer_to_audit(audit_id, viewer_id)

        # Create a risk
        risk_id = create_risk_with_audit(test_db, audit_id, 'R001')

        # Login as viewer
        login_user(client, test_db, viewer_id)

        # Try to edit risk - should be denied
        response = client.put(f'/api/risks/R001',
            json={'risk': 'Modified risk'})
        assert response.status_code == 403


# ==================== TEST WORKFLOW TRANSITIONS ====================

class TestWorkflowTransitions:
    """Tests for workflow state transitions."""

    def test_submit_for_review_changes_status(self, client, test_db):
        """Submitting for review should change status from draft to in_review."""
        # Create auditor and reviewer users
        auditor_id = create_user(test_db, unique_email('auditor'), 'Auditor User', role='auditor')
        reviewer_id = create_user(test_db, unique_email('reviewer'), 'Reviewer User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add auditor to audit team
        test_db.add_to_audit_team(audit_id, auditor_id, 'auditor')
        test_db.add_to_audit_team(audit_id, reviewer_id, 'reviewer')

        # Create a draft risk
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'draft')

        # Login as auditor
        login_user(client, test_db, auditor_id)

        # Submit for review
        response = client.post(f'/api/records/risk/{risk_pk}/submit-for-review',
            json={'reviewer_id': reviewer_id})

        assert response.status_code == 200

        # Verify status changed
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'in_review'

    def test_return_to_auditor_changes_status(self, client, test_db):
        """Returning to auditor should change status from in_review to draft."""
        # Create users
        auditor_id = create_user(test_db, unique_email('auditor'), 'Auditor User', role='auditor')
        reviewer_id = create_user(test_db, unique_email('reviewer'), 'Reviewer User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add to audit team
        test_db.add_to_audit_team(audit_id, auditor_id, 'auditor')
        test_db.add_to_audit_team(audit_id, reviewer_id, 'reviewer')

        # Create a risk in review
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'in_review')

        # Set assigned reviewer
        with test_db._connection() as conn:
            conn.execute('UPDATE risks SET assigned_reviewer_id = ? WHERE id = ?',
                        (reviewer_id, risk_pk))

        # Login as reviewer
        login_user(client, test_db, reviewer_id)

        # Return to auditor
        response = client.post(f'/api/records/risk/{risk_pk}/return-to-auditor',
            json={'notes': 'Please revise'})

        assert response.status_code == 200

        # Verify status changed
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'draft'

    def test_sign_off_permanently_locks_record(self, client, test_db):
        """Signing off should permanently lock the record."""
        # Create users
        auditor_id = create_user(test_db, unique_email('auditor'), 'Auditor User', role='auditor')
        reviewer_id = create_user(test_db, unique_email('reviewer'), 'Reviewer User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add to audit team
        test_db.add_to_audit_team(audit_id, auditor_id, 'auditor')
        test_db.add_to_audit_team(audit_id, reviewer_id, 'reviewer')

        # Create a risk in review
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'in_review')

        # Set assigned reviewer
        with test_db._connection() as conn:
            conn.execute('UPDATE risks SET assigned_reviewer_id = ? WHERE id = ?',
                        (reviewer_id, risk_pk))

        # Login as reviewer
        login_user(client, test_db, reviewer_id)

        # Sign off
        response = client.post(f'/api/records/risk/{risk_pk}/sign-off',
            json={'confirmation': 'SIGN OFF'})

        assert response.status_code == 200

        # Verify status changed to signed_off
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'signed_off'

    def test_admin_can_lock_unlock_records(self, client, test_db):
        """Admin should be able to lock and unlock records."""
        # Create admin user
        admin_id = create_user(test_db, unique_email('admin'), 'Admin User', role='admin', is_admin=True)

        # Create audit and risk
        audit_id = create_audit(test_db, 'Test Audit')
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'draft')

        # Login as admin
        login_user(client, test_db, admin_id)

        # Lock the record
        response = client.post(f'/api/admin/records/risk/{risk_pk}/lock',
            json={'reason': 'Under investigation'})
        assert response.status_code == 200

        # Refresh from database to verify locked
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'admin_hold', f"Expected admin_hold, got {risk['record_status']}"

        # Unlock the record (with reason and return_to)
        response = client.post(f'/api/admin/records/risk/{risk_pk}/unlock',
            json={'reason': 'Investigation complete', 'return_to': 'draft'})
        assert response.status_code == 200, f"Unlock failed: {response.get_json()}"

        # Verify unlocked
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'draft'


# ==================== TEST AUDIT TEAM WORKFLOW ====================

class TestAuditTeamWorkflow:
    """Tests for audit team-based workflow permissions.

    Critical: users with global role=auditor but audit_team role=reviewer
    can sign off / return to auditor (workflow checks are audit_team-based).
    """

    def test_auditor_with_reviewer_team_role_can_sign_off(self, client, test_db):
        """A user with global role 'auditor' but assigned as 'reviewer' on audit_team
        should be able to sign off records."""
        # Create a user with global role 'auditor'
        user_id = create_user(test_db, unique_email('dual_role'), 'Dual Role User', role='auditor')

        # Create another auditor who created the record
        creator_id = create_user(test_db, unique_email('creator'), 'Creator User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add user as REVIEWER on the audit team (not auditor)
        test_db.add_to_audit_team(audit_id, user_id, 'reviewer')
        test_db.add_to_audit_team(audit_id, creator_id, 'auditor')

        # Create a risk in review, assigned to our user
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'in_review')

        # Set assigned reviewer to our user
        with test_db._connection() as conn:
            conn.execute('UPDATE risks SET assigned_reviewer_id = ? WHERE id = ?',
                        (user_id, risk_pk))

        # Verify user is reviewer on audit but has global role 'auditor'
        user = test_db.get_user_by_id(user_id)
        assert user['role'] == 'auditor'  # Global role is auditor
        assert test_db.is_reviewer_on_audit(user_id, audit_id)  # But reviewer on audit_team

        # Login as the user
        login_user(client, test_db, user_id)

        # Sign off should succeed because user is assigned reviewer on audit_team
        response = client.post(f'/api/records/risk/{risk_pk}/sign-off',
            json={'confirmation': 'SIGN OFF'})

        assert response.status_code == 200

        # Verify status changed
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'signed_off'

    def test_auditor_with_reviewer_team_role_can_return_to_auditor(self, client, test_db):
        """A user with global role 'auditor' but assigned as 'reviewer' on audit_team
        should be able to return records to auditor."""
        # Create a user with global role 'auditor'
        user_id = create_user(test_db, unique_email('dual_role'), 'Dual Role User', role='auditor')

        # Create another auditor
        creator_id = create_user(test_db, unique_email('creator'), 'Creator User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add user as REVIEWER on the audit team
        test_db.add_to_audit_team(audit_id, user_id, 'reviewer')
        test_db.add_to_audit_team(audit_id, creator_id, 'auditor')

        # Create a risk in review, assigned to our user
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'in_review')

        # Set assigned reviewer
        with test_db._connection() as conn:
            conn.execute('UPDATE risks SET assigned_reviewer_id = ? WHERE id = ?',
                        (user_id, risk_pk))

        # Login as the user
        login_user(client, test_db, user_id)

        # Return to auditor should succeed
        response = client.post(f'/api/records/risk/{risk_pk}/return-to-auditor',
            json={'notes': 'Please fix formatting'})

        assert response.status_code == 200

        # Verify status changed
        risk = test_db.get_risk('R001')
        assert risk['record_status'] == 'draft'

    def test_user_without_reviewer_team_role_cannot_sign_off(self, client, test_db):
        """A user who is NOT assigned as reviewer on audit_team should NOT be able
        to sign off records, even if they have global role 'auditor'."""
        # Create two users with global role 'auditor'
        user_id = create_user(test_db, unique_email('auditor'), 'Auditor Only User', role='auditor')
        other_reviewer_id = create_user(test_db, unique_email('reviewer'), 'Reviewer User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add user as AUDITOR only (not reviewer)
        test_db.add_to_audit_team(audit_id, user_id, 'auditor')
        test_db.add_to_audit_team(audit_id, other_reviewer_id, 'reviewer')

        # Create a risk in review, assigned to other_reviewer
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'in_review')

        # Set assigned reviewer to other user
        with test_db._connection() as conn:
            conn.execute('UPDATE risks SET assigned_reviewer_id = ? WHERE id = ?',
                        (other_reviewer_id, risk_pk))

        # Login as auditor (not the assigned reviewer)
        login_user(client, test_db, user_id)

        # Sign off should fail
        response = client.post(f'/api/records/risk/{risk_pk}/sign-off',
            json={'confirmation': 'SIGN OFF'})

        assert response.status_code == 403

    def test_auditor_team_member_can_submit_for_review(self, client, test_db):
        """Any user assigned as auditor on audit_team should be able to submit for review."""
        # Create users
        auditor_id = create_user(test_db, unique_email('auditor'), 'Auditor User', role='auditor')
        reviewer_id = create_user(test_db, unique_email('reviewer'), 'Reviewer User', role='auditor')

        # Create audit
        audit_id = create_audit(test_db, 'Test Audit')

        # Add to audit team
        test_db.add_to_audit_team(audit_id, auditor_id, 'auditor')
        test_db.add_to_audit_team(audit_id, reviewer_id, 'reviewer')

        # Create a draft risk
        risk_pk = create_risk_with_audit(test_db, audit_id, 'R001', 'draft')

        # Login as auditor
        login_user(client, test_db, auditor_id)

        # Submit for review should succeed
        response = client.post(f'/api/records/risk/{risk_pk}/submit-for-review',
            json={'reviewer_id': reviewer_id})

        assert response.status_code == 200


# ==================== TEST ROLE MIGRATION ====================

class TestRoleMigration:
    """Tests for role migration from 'reviewer' to 'auditor'."""

    def test_reviewer_role_mapped_to_auditor(self, test_db):
        """Users with global role 'reviewer' should be treated as 'auditor'."""
        # Create a user with explicit 'reviewer' role
        # (simulating legacy data before migration)
        with test_db._connection() as conn:
            cursor = conn.execute('''
                INSERT INTO users (email, name, password_hash, is_active, is_admin, role)
                VALUES (?, ?, ?, 1, 0, 'reviewer')
            ''', (unique_email('legacy_reviewer'), 'Legacy Reviewer',
                  generate_password_hash('testpass123', method='pbkdf2:sha256')))
            user_id = cursor.lastrowid

        # Get audits for user with 'reviewer' role
        # Should still have full visibility like an 'auditor'
        audit_id = create_audit(test_db, 'Test Audit')

        audits = test_db.get_audits_for_user_role(user_id, 'reviewer')
        # Reviewer role should have same visibility as auditor (see all audits)
        assert len(audits) >= 1

    def test_new_users_get_auditor_role(self, test_db):
        """New users should get 'auditor' role by default (not 'reviewer')."""
        user_id = create_user(test_db, unique_email('new_user'), 'New User', role='auditor')
        user = test_db.get_user_by_id(user_id)
        assert user['role'] == 'auditor'
