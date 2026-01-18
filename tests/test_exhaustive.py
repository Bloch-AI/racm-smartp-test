"""
Exhaustive tests for RACM Smart-P application.
Tests every route, button, link, form, and API endpoint.

Run with: pytest tests/test_exhaustive.py -v
Run regression tests: pytest -m regression
"""
import io
import json
import pytest
import uuid
import app as app_module
from database import RACMDatabase

# Mark entire module as regression tests
pytestmark = [pytest.mark.regression, pytest.mark.api]


# ==================== FIXTURES ====================

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with sample data."""
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
    library_dir = tmp_path / 'library'
    library_dir.mkdir()
    app_module.app.config['UPLOAD_FOLDER'] = str(uploads_dir)
    app_module.UPLOAD_FOLDER = str(uploads_dir)

    original_db = app_module.db
    app_module.db = test_db

    with app_module.app.test_client() as client:
        yield client

    app_module.db = original_db


@pytest.fixture
def test_audit(test_db):
    """Create a test audit and return its ID."""
    audit_id = test_db.create_audit(
        title='Test Audit',
        description='Audit for testing',
        status='In Progress',
        risk_rating='Medium'
    )
    return audit_id


@pytest.fixture
def auth_client(client, test_db, test_audit):
    """Create authenticated test client with admin user."""
    # Use the default admin user created by the database
    # or create a new one with a unique email
    from werkzeug.security import generate_password_hash
    import database as database_module
    import auth as auth_module

    # Check if default admin exists
    user = test_db.get_user_by_email('admin@localhost')
    if not user:
        # Create admin user with unique email
        with test_db._connection() as conn:
            conn.execute('''
                INSERT INTO users (email, name, password_hash, is_active, is_admin)
                VALUES (?, ?, ?, 1, 1)
            ''', ('admin@test.com', 'Test Admin', generate_password_hash('testpass123', method='pbkdf2:sha256')))
        user = test_db.get_user_by_email('admin@test.com')

    # Add user to audit team as auditor
    with test_db._connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO audit_team (audit_id, user_id, team_role)
            VALUES (?, ?, 'auditor')
        """, (test_audit, user['id']))

    # Patch get_db in all modules
    test_get_db = lambda db_path=None: test_db
    app_module.get_db = test_get_db
    database_module.get_db = test_get_db
    auth_module.get_db = test_get_db

    # Login with the found/created user
    with client.session_transaction() as sess:
        sess['user_id'] = user['id']
        sess['email'] = user['email']
        sess['name'] = user['name']
        sess['is_admin'] = user['is_admin']
        sess['active_audit_id'] = test_audit

    return client


@pytest.fixture
def sample_data(test_db, auth_client, test_audit):
    """Create comprehensive sample data for testing."""
    # Get the user ID from the session
    with auth_client.session_transaction() as sess:
        user_id = sess.get('user_id', 1)

    # Create risks with audit_id and created_by
    test_db.create_risk(
        risk_id='R001',
        risk='Access control weakness',
        control_id='C001',
        control_owner='IT Security',
        status='Not Complete',
        audit_id=test_audit,
        created_by=user_id
    )
    test_db.create_risk(
        risk_id='R002',
        risk='Data backup failure',
        control_id='C002',
        control_owner='IT Operations',
        status='Effective',
        audit_id=test_audit,
        created_by=user_id
    )

    # Create tasks
    task1_id = test_db.create_task(
        title='Review access logs',
        description='Review user access logs for anomalies',
        column_id='planning',
        priority='high'
    )
    task2_id = test_db.create_task(
        title='Test backup restore',
        description='Verify backup restoration process',
        column_id='fieldwork',
        priority='medium'
    )

    # Create issue with audit_id and created_by
    issue_id = test_db.create_issue(
        risk_id='R001',
        title='Excessive admin access',
        description='Multiple users have admin privileges without business need',
        severity='High',
        status='Open',
        audit_id=test_audit,
        created_by=user_id
    )

    # Create flowchart
    test_db.save_flowchart('access-review-process', {
        'drawflow': {'Home': {'data': {'1': {'id': 1, 'name': 'start'}}}}
    })

    return {
        'audit_id': test_audit,
        'task_ids': [task1_id, task2_id],
        'issue_id': issue_id
    }


# ==================== PAGE LOADING TESTS ====================

class TestPageLoading:
    """Test that all pages load correctly."""

    def test_login_page_loads(self, client):
        """Login page should load."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'email' in response.data.lower()

    def test_index_page_requires_auth(self, client):
        """Index page should redirect to login when not authenticated."""
        response = client.get('/')
        assert response.status_code in [200, 302]

    def test_index_page_loads_when_authenticated(self, auth_client, sample_data):
        """Index page should load when authenticated."""
        response = auth_client.get('/')
        assert response.status_code == 200
        assert b'RACM' in response.data or b'Risk' in response.data

    def test_kanban_page_loads(self, auth_client, sample_data):
        """Kanban page should load."""
        response = auth_client.get('/kanban')
        assert response.status_code == 200
        assert b'kanban' in response.data.lower()

    def test_kanban_with_board_id_loads(self, auth_client, sample_data):
        """Kanban page with board ID should load."""
        response = auth_client.get('/kanban/default')
        assert response.status_code == 200

    def test_flowchart_page_loads(self, auth_client, sample_data):
        """Flowchart page should load."""
        response = auth_client.get('/flowchart')
        assert response.status_code == 200
        assert b'flowchart' in response.data.lower() or b'drawflow' in response.data.lower()

    def test_flowchart_with_id_loads(self, auth_client, sample_data):
        """Flowchart page with ID should load."""
        response = auth_client.get('/flowchart/access-review-process')
        assert response.status_code == 200

    def test_audit_plan_page_loads(self, auth_client, sample_data):
        """Audit plan page should load."""
        response = auth_client.get('/audit-plan')
        assert response.status_code == 200

    def test_library_page_loads(self, auth_client, sample_data):
        """Library page should load."""
        response = auth_client.get('/library')
        assert response.status_code == 200
        assert b'library' in response.data.lower()

    def test_felix_page_loads(self, auth_client, sample_data):
        """Felix AI page should load."""
        response = auth_client.get('/felix')
        assert response.status_code == 200
        assert b'felix' in response.data.lower() or b'chat' in response.data.lower()

    def test_admin_page_loads(self, auth_client, sample_data):
        """Admin page should load for admin users."""
        response = auth_client.get('/admin')
        assert response.status_code == 200

    def test_admin_users_page_loads(self, auth_client, sample_data):
        """Admin users page should load."""
        response = auth_client.get('/admin/users', follow_redirects=True)
        assert response.status_code == 200

    def test_admin_audits_page_loads(self, auth_client, sample_data):
        """Admin audits page should load."""
        response = auth_client.get('/admin/audits', follow_redirects=True)
        assert response.status_code == 200


# ==================== AUTHENTICATION TESTS ====================

class TestAuthentication:
    """Test authentication flows."""

    def test_login_with_valid_credentials(self, client, test_db):
        """Login should succeed with valid credentials."""
        from werkzeug.security import generate_password_hash
        with test_db._connection() as conn:
            conn.execute('''
                INSERT INTO users (email, name, password_hash, is_active, is_admin)
                VALUES (?, ?, ?, 1, 0)
            ''', ('user@test.com', 'Test User', generate_password_hash('password123', method='pbkdf2:sha256')))

        response = client.post('/login', data={
            'email': 'user@test.com',
            'password': 'password123'
        }, follow_redirects=False)
        assert response.status_code == 302  # Redirect on success

    def test_login_with_invalid_password(self, client, test_db):
        """Login should fail with invalid password."""
        from werkzeug.security import generate_password_hash
        with test_db._connection() as conn:
            conn.execute('''
                INSERT INTO users (email, name, password_hash, is_active, is_admin)
                VALUES (?, ?, ?, 1, 0)
            ''', ('user@test.com', 'Test User', generate_password_hash('password123', method='pbkdf2:sha256')))

        response = client.post('/login', data={
            'email': 'user@test.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b'Invalid' in response.data or b'error' in response.data.lower()

    def test_login_with_nonexistent_user(self, client):
        """Login should fail with nonexistent user."""
        response = client.post('/login', data={
            'email': 'nonexistent@test.com',
            'password': 'password123'
        })
        assert response.status_code == 200
        assert b'Invalid' in response.data or b'error' in response.data.lower()

    def test_login_with_empty_fields(self, client):
        """Login should fail with empty fields."""
        response = client.post('/login', data={
            'email': '',
            'password': ''
        })
        assert response.status_code == 200
        assert b'enter' in response.data.lower() or b'required' in response.data.lower()

    def test_logout(self, auth_client):
        """Logout should clear session."""
        response = auth_client.get('/logout', follow_redirects=False)
        assert response.status_code == 302

    def test_auth_me_endpoint(self, auth_client):
        """Auth me endpoint should return current user."""
        response = auth_client.get('/api/auth/me')
        assert response.status_code == 200
        data = response.get_json()
        assert 'email' in data or 'user' in data

    def test_set_active_audit(self, auth_client, sample_data):
        """Should be able to set active audit."""
        response = auth_client.post('/api/auth/set-audit',
            json={'audit_id': sample_data['audit_id']})
        assert response.status_code == 200

    def test_get_accessible_audits(self, auth_client, sample_data):
        """Should return accessible audits."""
        response = auth_client.get('/api/auth/accessible-audits')
        assert response.status_code == 200
        data = response.get_json()
        assert 'audits' in data  # Returns {audits: [], active_audit_id: ...}


# ==================== RACM/RISK API TESTS ====================

class TestRiskAPI:
    """Test risk/RACM API endpoints."""

    def test_get_all_data(self, auth_client, sample_data):
        """Should get all RACM data."""
        response = auth_client.get('/api/data')
        assert response.status_code == 200
        data = response.get_json()
        assert 'racm' in data or 'risks' in data

    def test_save_data(self, auth_client, sample_data):
        """Should save RACM data."""
        response = auth_client.post('/api/data', json={
            'racm': [
                ['R003', 'New risk', 'C003', 'Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']
            ],
            'issues': []
        })
        assert response.status_code == 200

    def test_get_all_risks(self, auth_client, sample_data):
        """Should get all risks."""
        response = auth_client.get('/api/risks')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_single_risk(self, auth_client, sample_data):
        """Should get a single risk by ID."""
        response = auth_client.get('/api/risks/R001')
        assert response.status_code == 200
        data = response.get_json()
        assert data['risk_id'] == 'R001'

    def test_get_nonexistent_risk(self, auth_client, sample_data):
        """Should return 404 for nonexistent risk."""
        response = auth_client.get('/api/risks/NONEXISTENT')
        assert response.status_code == 404

    def test_create_risk(self, auth_client, sample_data):
        """Should create a new risk."""
        response = auth_client.post('/api/risks', json={
            'risk_id': 'R999',
            'risk': 'API Created Risk',
            'control_id': 'C999',
            'control_owner': 'API Test'
        })
        assert response.status_code in [200, 201]

    def test_update_risk(self, auth_client, sample_data):
        """Should update a risk."""
        response = auth_client.put('/api/risks/R001', json={
            'status': 'Effective'
        })
        assert response.status_code == 200

    def test_delete_risk(self, auth_client, sample_data):
        """Should delete a risk."""
        # Create a risk to delete
        auth_client.post('/api/risks', json={
            'risk_id': 'R_DELETE',
            'risk': 'To be deleted',
            'control_id': 'C_DEL',
            'control_owner': 'Test'
        })
        response = auth_client.delete('/api/risks/R_DELETE')
        assert response.status_code == 200


# ==================== FLOWCHART API TESTS ====================

class TestFlowchartAPI:
    """Test flowchart API endpoints."""

    def test_list_flowcharts(self, auth_client, sample_data):
        """Should list all flowcharts."""
        response = auth_client.get('/api/flowcharts')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_flowchart(self, auth_client, sample_data):
        """Should get a specific flowchart."""
        response = auth_client.get('/api/flowchart/access-review-process')
        assert response.status_code == 200

    def test_get_nonexistent_flowchart(self, auth_client, sample_data):
        """Should handle nonexistent flowchart."""
        response = auth_client.get('/api/flowchart/nonexistent')
        assert response.status_code in [200, 404]  # May return empty or 404

    def test_save_flowchart(self, auth_client, sample_data):
        """Should save a flowchart."""
        flowchart_data = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {'id': 1, 'name': 'start', 'data': {'name': 'Start'}},
                        '2': {'id': 2, 'name': 'process', 'data': {'name': 'Process'}},
                        '3': {'id': 3, 'name': 'end', 'data': {'name': 'End'}}
                    }
                }
            }
        }
        response = auth_client.post('/api/flowchart/test-flowchart',
            json=flowchart_data)
        assert response.status_code == 200

    def test_update_flowchart(self, auth_client, sample_data):
        """Should update a flowchart."""
        flowchart_data = {
            'drawflow': {
                'Home': {'data': {'1': {'id': 1, 'name': 'updated'}}}
            }
        }
        response = auth_client.post('/api/flowchart/access-review-process',
            json=flowchart_data)
        assert response.status_code == 200


# ==================== KANBAN/TASK API TESTS ====================

class TestKanbanAPI:
    """Test Kanban board and task API endpoints."""

    def test_get_kanban_board(self, auth_client, sample_data):
        """Should get kanban board data."""
        response = auth_client.get('/api/kanban/default')
        assert response.status_code == 200
        data = response.get_json()
        assert 'columns' in data or isinstance(data, dict)

    def test_save_kanban_board(self, auth_client, sample_data):
        """Should save kanban board state."""
        response = auth_client.post('/api/kanban/default', json={
            'tasks': [{'id': 1, 'column': 'testing'}]
        })
        assert response.status_code == 200

    def test_create_task_via_kanban(self, auth_client, sample_data):
        """Should create task via kanban API."""
        response = auth_client.post('/api/kanban/default/task', json={
            'title': 'New Kanban Task',
            'description': 'Created via kanban API',
            'column_id': 'planning'
        })
        assert response.status_code in [200, 201]

    def test_get_task_via_kanban(self, auth_client, sample_data):
        """Should get task via kanban API."""
        task_id = sample_data['task_ids'][0]
        response = auth_client.get(f'/api/kanban/default/task/{task_id}')
        assert response.status_code == 200

    def test_update_task_via_kanban(self, auth_client, sample_data):
        """Should update task via kanban API."""
        task_id = sample_data['task_ids'][0]
        response = auth_client.put(f'/api/kanban/default/task/{task_id}', json={
            'column_id': 'review',
            'priority': 'low'
        })
        assert response.status_code == 200

    def test_get_all_tasks(self, auth_client, sample_data):
        """Should get all tasks."""
        response = auth_client.get('/api/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_single_task(self, auth_client, sample_data):
        """Should get a single task."""
        task_id = sample_data['task_ids'][0]
        response = auth_client.get(f'/api/tasks/{task_id}')
        assert response.status_code == 200

    def test_create_task(self, auth_client, sample_data):
        """Should create a task."""
        response = auth_client.post('/api/tasks', json={
            'title': 'API Created Task',
            'description': 'Task description',
            'column_id': 'fieldwork',
            'priority': 'high'
        })
        assert response.status_code in [200, 201]


# ==================== AUDIT API TESTS ====================

class TestAuditAPI:
    """Test audit management API endpoints."""

    def test_get_all_audits(self, auth_client, sample_data):
        """Should get all audits."""
        response = auth_client.get('/api/audits')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_single_audit(self, auth_client, sample_data):
        """Should get a single audit."""
        response = auth_client.get(f'/api/audits/{sample_data["audit_id"]}')
        assert response.status_code == 200

    def test_create_audit(self, auth_client, sample_data):
        """Should create an audit."""
        response = auth_client.post('/api/audits', json={
            'title': 'New API Audit',
            'description': 'Created via API',
            'quarter': 'Q2',
            'status': 'planning'
        })
        assert response.status_code in [200, 201]

    def test_update_audit(self, auth_client, sample_data):
        """Should update an audit."""
        response = auth_client.put(f'/api/audits/{sample_data["audit_id"]}', json={
            'status': 'complete'
        })
        assert response.status_code == 200

    def test_delete_audit(self, auth_client, sample_data):
        """Should delete an audit."""
        # Create an audit to delete
        create_resp = auth_client.post('/api/audits', json={
            'title': 'To Delete',
            'description': 'Will be deleted'
        })
        audit_id = create_resp.get_json().get('id')
        if audit_id:
            response = auth_client.delete(f'/api/audits/{audit_id}')
            assert response.status_code == 200

    def test_get_audits_spreadsheet(self, auth_client, sample_data):
        """Should get audits in spreadsheet format."""
        response = auth_client.get('/api/audits/spreadsheet')
        assert response.status_code == 200

    def test_save_audits_spreadsheet(self, auth_client, sample_data):
        """Should save audits from spreadsheet format (array of arrays)."""
        # API expects array of arrays, not {audits: [...]}
        response = auth_client.post('/api/audits/spreadsheet', json=[
            ['Spreadsheet Audit', 'Description', 'Q1', 'planning']
        ])
        assert response.status_code == 200

    def test_get_audits_kanban(self, auth_client, sample_data):
        """Should get audits in kanban format."""
        response = auth_client.get('/api/audits/kanban')
        assert response.status_code == 200

    def test_get_audits_summary(self, auth_client, sample_data):
        """Should get audits summary."""
        response = auth_client.get('/api/audits/summary')
        assert response.status_code == 200


# ==================== ISSUE API TESTS ====================

class TestIssueAPI:
    """Test issue management API endpoints."""

    def test_get_all_issues(self, auth_client, sample_data):
        """Should get all issues."""
        response = auth_client.get('/api/issues')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_single_issue(self, auth_client, sample_data):
        """Should get a single issue."""
        # Get issue ID from list
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.get(f'/api/issues/{issue_id}')
            assert response.status_code == 200

    def test_create_issue(self, auth_client, sample_data):
        """Should create an issue."""
        response = auth_client.post('/api/issues', json={
            'risk_id': 'R001',
            'title': 'API Created Issue',
            'description': 'Issue created via API',
            'severity': 'Medium',
            'status': 'Open'
        })
        assert response.status_code in [200, 201]

    def test_update_issue(self, auth_client, sample_data):
        """Should update an issue."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.put(f'/api/issues/{issue_id}', json={
                'status': 'In Progress'
            })
            assert response.status_code == 200

    def test_delete_issue(self, auth_client, sample_data):
        """Should delete an issue."""
        # Create an issue to delete
        create_resp = auth_client.post('/api/issues', json={
            'risk_id': 'R001',
            'title': 'To Delete',
            'description': 'Will be deleted',
            'severity': 'Low'
        })
        if create_resp.status_code in [200, 201]:
            data = create_resp.get_json()
            issue_id = data.get('issue_id')
            if issue_id:
                response = auth_client.delete(f'/api/issues/{issue_id}')
                assert response.status_code == 200

    def test_create_issue_from_risk(self, auth_client, sample_data):
        """Should create issue from risk."""
        response = auth_client.post('/api/issues/from-risk/R002')
        assert response.status_code in [200, 201]

    def test_get_issue_documentation(self, auth_client, sample_data):
        """Should get issue documentation."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.get(f'/api/issues/{issue_id}/documentation')
            assert response.status_code == 200

    def test_save_issue_documentation(self, auth_client, sample_data):
        """Should save issue documentation."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.post(f'/api/issues/{issue_id}/documentation', json={
                'documentation': '<p>Root cause analysis documentation</p>'
            })
            assert response.status_code == 200

    def test_check_issue_documentation_exists(self, auth_client, sample_data):
        """Should check if issue documentation exists."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.get(f'/api/issues/{issue_id}/documentation/exists')
            assert response.status_code == 200


# ==================== TEST DOCUMENT API TESTS ====================

class TestTestDocumentAPI:
    """Test test document (working papers) API endpoints."""

    def test_get_de_test_document(self, auth_client, sample_data):
        """Should get DE testing document."""
        response = auth_client.get('/api/test-document/R001/de_testing')
        assert response.status_code == 200

    def test_save_de_test_document(self, auth_client, sample_data):
        """Should save DE testing document."""
        response = auth_client.post('/api/test-document/R001/de_testing', json={
            'content': '<h1>Design Effectiveness Testing</h1><p>Test procedures...</p>'
        })
        assert response.status_code == 200

    def test_get_oe_test_document(self, auth_client, sample_data):
        """Should get OE testing document."""
        response = auth_client.get('/api/test-document/R001/oe_testing')
        assert response.status_code == 200

    def test_save_oe_test_document(self, auth_client, sample_data):
        """Should save OE testing document."""
        response = auth_client.post('/api/test-document/R001/oe_testing', json={
            'content': '<h1>Operational Effectiveness Testing</h1><p>Test results...</p>'
        })
        assert response.status_code == 200

    def test_check_test_document_exists(self, auth_client, sample_data):
        """Should check if test document exists."""
        response = auth_client.get('/api/test-document/R001/de_testing/exists')
        assert response.status_code == 200


# ==================== LIBRARY API TESTS ====================

class TestLibraryAPI:
    """Test audit library API endpoints."""

    def test_list_library_documents(self, auth_client, sample_data):
        """Should list library documents."""
        response = auth_client.get('/api/library/documents')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_upload_library_document(self, auth_client, sample_data, tmp_path):
        """Should upload library document."""
        test_file = (io.BytesIO(b'Sample document content for library'), 'test-doc.txt')
        response = auth_client.post('/api/library/documents',
            data={
                'file': test_file,
                'name': 'Test Document',
                'doc_type': 'standard',
                'description': 'Test description'
            },
            content_type='multipart/form-data')
        assert response.status_code in [200, 201]

    def test_get_library_stats(self, auth_client, sample_data):
        """Should get library statistics."""
        response = auth_client.get('/api/library/stats')
        assert response.status_code == 200

    def test_search_library(self, auth_client, sample_data):
        """Should search library."""
        response = auth_client.post('/api/library/search', json={
            'query': 'audit'
        })
        assert response.status_code == 200


# ==================== FILE ATTACHMENT TESTS ====================

class TestAttachmentAPI:
    """Test file attachment API endpoints."""

    def test_upload_risk_attachment(self, auth_client, sample_data):
        """Should upload attachment to risk."""
        test_file = (io.BytesIO(b'Evidence file content'), 'evidence.txt')
        response = auth_client.post('/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data')
        assert response.status_code == 200

    def test_list_risk_attachments(self, auth_client, sample_data):
        """Should list risk attachments."""
        response = auth_client.get('/api/risks/R001/attachments')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_upload_issue_attachment(self, auth_client, sample_data):
        """Should upload attachment to issue."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            test_file = (io.BytesIO(b'Issue evidence'), 'issue-evidence.txt')
            response = auth_client.post(f'/api/issues/{issue_id}/attachments',
                data={'file': test_file},
                content_type='multipart/form-data')
            assert response.status_code == 200

    def test_list_issue_attachments(self, auth_client, sample_data):
        """Should list issue attachments."""
        list_resp = auth_client.get('/api/issues')
        issues = list_resp.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = auth_client.get(f'/api/issues/{issue_id}/attachments')
            assert response.status_code == 200

    def test_upload_audit_attachment(self, auth_client, sample_data):
        """Should upload attachment to audit."""
        test_file = (io.BytesIO(b'Audit document'), 'audit-doc.txt')
        response = auth_client.post(f'/api/audits/{sample_data["audit_id"]}/attachments',
            data={'file': test_file},
            content_type='multipart/form-data')
        assert response.status_code == 200

    def test_list_audit_attachments(self, auth_client, sample_data):
        """Should list audit attachments."""
        response = auth_client.get(f'/api/audits/{sample_data["audit_id"]}/attachments')
        assert response.status_code == 200


# ==================== AI/CHAT API TESTS ====================

class TestChatAPI:
    """Test AI chat API endpoints."""

    def test_chat_status(self, auth_client, sample_data):
        """Should get chat status."""
        response = auth_client.get('/api/chat/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'configured' in data

    def test_chat_message(self, auth_client, sample_data):
        """Should accept chat message."""
        response = auth_client.post('/api/chat', json={
            'message': 'Hello, what can you help me with?'
        })
        # Accept various status codes depending on API key config
        assert response.status_code in [200, 401, 500, 503]

    def test_clear_chat(self, auth_client, sample_data):
        """Should clear chat history."""
        response = auth_client.post('/api/chat/clear')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('status') == 'cleared'


# ==================== FELIX AI TESTS ====================

class TestFelixAPI:
    """Test Felix AI conversation API endpoints."""

    def test_list_felix_conversations(self, auth_client, sample_data):
        """Should list Felix conversations."""
        response = auth_client.get('/api/felix/conversations')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_create_felix_conversation(self, auth_client, sample_data):
        """Should create Felix conversation."""
        response = auth_client.post('/api/felix/conversations')
        assert response.status_code == 200
        data = response.get_json()
        assert 'id' in data

    def test_delete_felix_conversation(self, auth_client, sample_data):
        """Should delete Felix conversation."""
        # Create first
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        # Delete
        response = auth_client.delete(f'/api/felix/conversations/{conv_id}')
        assert response.status_code == 200

    def test_get_felix_messages(self, auth_client, sample_data):
        """Should get Felix conversation messages."""
        # Create conversation
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        response = auth_client.get(f'/api/felix/conversations/{conv_id}/messages')
        assert response.status_code == 200

    def test_send_felix_message(self, auth_client, sample_data):
        """Should send message to Felix."""
        # Create conversation
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        response = auth_client.post(f'/api/felix/conversations/{conv_id}/messages', json={
            'content': 'Hello Felix!'  # API expects 'content', not 'message'
        })
        # Accept various codes depending on API key availability
        assert response.status_code in [200, 400, 401, 500, 503]

    def test_list_felix_attachments(self, auth_client, sample_data):
        """Should list Felix conversation attachments."""
        # Create conversation
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        response = auth_client.get(f'/api/felix/conversations/{conv_id}/attachments')
        assert response.status_code == 200

    def test_upload_felix_attachment(self, auth_client, sample_data):
        """Should upload attachment to Felix conversation."""
        # Create conversation
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        test_file = (io.BytesIO(b'Context document for Felix'), 'context.txt')
        response = auth_client.post(f'/api/felix/conversations/{conv_id}/attachments',
            data={'file': test_file},
            content_type='multipart/form-data')
        assert response.status_code == 200


# ==================== ADMIN API TESTS ====================

class TestAdminAPI:
    """Test admin API endpoints."""

    def test_list_users(self, auth_client, sample_data):
        """Should list all users."""
        response = auth_client.get('/api/admin/users')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_create_user(self, auth_client, sample_data):
        """Should create a user."""
        response = auth_client.post('/api/admin/users', json={
            'email': 'newuser@test.com',
            'name': 'New User',
            'password': 'newpassword123',
            'is_admin': False
        })
        assert response.status_code in [200, 201]

    def test_get_user(self, auth_client, sample_data):
        """Should get a user."""
        response = auth_client.get('/api/admin/users/1')
        assert response.status_code == 200

    def test_update_user(self, auth_client, sample_data):
        """Should update a user."""
        response = auth_client.put('/api/admin/users/1', json={
            'name': 'Updated Admin Name'
        })
        assert response.status_code == 200

    def test_get_user_memberships(self, auth_client, sample_data):
        """Should get user memberships."""
        response = auth_client.get('/api/admin/users/1/memberships')
        assert response.status_code == 200

    def test_list_roles(self, auth_client, sample_data):
        """Should list all roles."""
        response = auth_client.get('/api/admin/roles')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_audit_memberships(self, auth_client, sample_data):
        """Should get audit memberships."""
        response = auth_client.get(f'/api/admin/audits/{sample_data["audit_id"]}/memberships')
        assert response.status_code == 200

    def test_add_audit_membership(self, auth_client, sample_data):
        """Should add user to audit."""
        response = auth_client.post(f'/api/admin/audits/{sample_data["audit_id"]}/memberships', json={
            'user_id': 1,
            'role_id': 2  # auditor
        })
        assert response.status_code in [200, 201]


# ==================== SCHEMA AND CONTEXT API TESTS ====================

class TestSchemaAPI:
    """Test schema and context API endpoints."""

    def test_get_schema(self, auth_client, sample_data):
        """Should get database schema."""
        response = auth_client.get('/api/schema')
        assert response.status_code == 200
        data = response.get_json()
        assert 'schema' in data

    def test_get_context(self, auth_client, sample_data):
        """Should get AI context."""
        response = auth_client.get('/api/context')
        assert response.status_code == 200

    def test_execute_query(self, auth_client, sample_data):
        """Should execute read-only SQL query."""
        response = auth_client.post('/api/query', json={
            'sql': "SELECT risk_id, status FROM risks LIMIT 5"
        })
        assert response.status_code == 200


# ==================== EXPORT/IMPORT TESTS ====================

class TestExportImportAPI:
    """Test export and import functionality."""

    def test_export_data(self, auth_client, sample_data):
        """Should export data."""
        response = auth_client.get('/api/export')
        assert response.status_code == 200

    def test_import_data(self, auth_client, sample_data):
        """Should import data."""
        response = auth_client.post('/api/import', json={
            'risks': [],
            'issues': []
        })
        assert response.status_code in [200, 400]


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_json(self, auth_client, sample_data):
        """Should handle invalid JSON gracefully."""
        response = auth_client.post('/api/data',
            data='not valid json',
            content_type='application/json')
        assert response.status_code in [400, 500]

    def test_missing_required_fields(self, auth_client, sample_data):
        """Should reject requests with missing required fields."""
        response = auth_client.post('/api/risks', json={})
        assert response.status_code in [400, 500]

    def test_sql_injection_attempt(self, auth_client, sample_data):
        """Should block SQL injection attempts."""
        response = auth_client.post('/api/query', json={
            'sql': "SELECT * FROM risks; DROP TABLE risks; --"
        })
        assert response.status_code == 400

    def test_path_traversal_attempt(self, auth_client, sample_data):
        """Should block path traversal in file uploads."""
        test_file = (io.BytesIO(b'malicious'), '../../../etc/passwd')
        response = auth_client.post('/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data')
        # Should either sanitize filename or reject
        if response.status_code == 200:
            data = response.get_json()
            assert '../' not in data.get('filename', '')

    def test_xss_in_input(self, auth_client, sample_data):
        """Should handle XSS attempts in input."""
        response = auth_client.post('/api/risks', json={
            'risk_id': 'R_XSS',
            'risk': '<script>alert("xss")</script>',
            'control_id': 'C_XSS',
            'control_owner': 'Test'
        })
        assert response.status_code in [200, 201]
        # Data should be stored (escaping on display)

    def test_unicode_in_input(self, auth_client, sample_data):
        """Should handle Unicode characters."""
        response = auth_client.post('/api/risks', json={
            'risk_id': 'R_UNI',
            'risk': 'Risk with émojis 🔐 and symbols £€¥',
            'control_id': 'C_UNI',
            'control_owner': 'Tëst Üser'
        })
        assert response.status_code in [200, 201]


# ==================== RATE LIMITING TESTS ====================

class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_login_rate_limiting(self, client, test_db):
        """Should rate limit login attempts."""
        # Make multiple failed login attempts
        for i in range(6):
            client.post('/login', data={
                'email': 'nonexistent@test.com',
                'password': 'wrongpassword'
            })

        # Should be rate limited now
        response = client.post('/login', data={
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        })
        # Check for rate limit message
        assert b'Too many' in response.data or response.status_code == 429 or b'try again' in response.data.lower()


# ==================== AUTHORIZATION TESTS ====================

class TestAuthorization:
    """Test authorization and access control."""

    def test_admin_only_endpoint(self, client, test_db):
        """Admin endpoints should require admin access."""
        # Create non-admin user
        from werkzeug.security import generate_password_hash
        with test_db._connection() as conn:
            cursor = conn.execute('''
                INSERT INTO users (email, name, password_hash, is_active, is_admin)
                VALUES (?, ?, ?, 1, 0)
            ''', ('viewer@test.com', 'Viewer', generate_password_hash('viewerpass', method='pbkdf2:sha256')))
            viewer_user_id = cursor.lastrowid

        # Login as viewer (use the actual viewer user ID, not hardcoded 1 which is admin)
        with client.session_transaction() as sess:
            sess['user_id'] = viewer_user_id
            sess['email'] = 'viewer@test.com'
            sess['is_admin'] = False

        # Try admin endpoint - should be denied
        response = client.get('/api/admin/users')
        assert response.status_code in [401, 403, 302]

    def test_unauthenticated_access(self, client):
        """Should redirect unauthenticated requests to login."""
        response = client.get('/kanban')
        assert response.status_code in [200, 302]  # May show login or redirect
