"""
Comprehensive Test Suite for RACM Audit Toolkit
Run with: pytest test_app.py -v

Includes:
- Unit tests for database.py
- Unit tests for app.py helpers
- Integration tests for API endpoints
- UAT (User Acceptance Testing) for complete workflows
"""
import pytest
import json
import sys
import os
import tempfile
import shutil

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import RACMDatabase
import app as app_module


# ==================== FIXTURES ====================

@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = RACMDatabase(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def client(test_db, tmp_path):
    """Create test client with isolated database."""
    # Point app to test database
    app_module.app.config['TESTING'] = True

    # Create test uploads directory
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir()
    app_module.app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    # Patch both get_db and the module-level db instance
    original_get_db = app_module.get_db
    original_db = app_module.db
    app_module.get_db = lambda: test_db
    app_module.db = test_db

    with app_module.app.test_client() as client:
        yield client

    # Restore originals
    app_module.get_db = original_get_db
    app_module.db = original_db


@pytest.fixture
def sample_risk(test_db):
    """Create a sample risk for testing."""
    risk_id = test_db.create_risk(
        risk_id='R001',
        risk='Sample test risk description',
        control_id='C001',
        control_owner='Test Owner',
        status='Not Complete'
    )
    return risk_id


@pytest.fixture
def sample_issue(test_db, sample_risk):
    """Create a sample issue for testing."""
    issue_id = test_db.create_issue(
        risk_id='R001',
        title='Sample Issue',
        description='Test issue description',
        severity='High',
        status='Open'
    )
    return issue_id


# ==================== UNIT TESTS: DATABASE ====================

class TestDatabaseRisks:
    """Unit tests for risks/RACM database operations."""

    def test_add_risk(self, test_db):
        """Test adding a new risk."""
        risk_id = test_db.create_risk(
            risk_id='R001',
            risk='Test risk',
            control_id='C001',
            control_owner='Owner'
        )
        assert risk_id is not None

    def test_get_risk(self, test_db, sample_risk):
        """Test retrieving a risk."""
        risk = test_db.get_risk('R001')
        assert risk is not None
        assert risk['risk_id'] == 'R001'
        assert risk['risk'] == 'Sample test risk description'

    def test_get_nonexistent_risk(self, test_db):
        """Test retrieving non-existent risk returns None."""
        risk = test_db.get_risk('NONEXISTENT')
        assert risk is None

    def test_update_risk(self, test_db, sample_risk):
        """Test updating a risk."""
        test_db.update_risk('R001', status='Effective', reviewer='Test Reviewer')
        risk = test_db.get_risk('R001')
        assert risk['status'] == 'Effective'
        assert risk['reviewer'] == 'Test Reviewer'

    def test_get_all_risks(self, test_db):
        """Test getting all risks."""
        test_db.create_risk(risk_id='R001', risk='Risk 1')
        test_db.create_risk(risk_id='R002', risk='Risk 2')
        test_db.create_risk(risk_id='R003', risk='Risk 3')

        risks = test_db.get_all_risks()
        assert len(risks) == 3

    def test_get_as_spreadsheet(self, test_db, sample_risk):
        """Test spreadsheet format export."""
        data = test_db.get_as_spreadsheet()
        assert isinstance(data, list)
        # Should have at least one row
        assert len(data) >= 1


class TestDatabaseIssues:
    """Unit tests for issues database operations."""

    def test_create_issue(self, test_db, sample_risk):
        """Test creating an issue."""
        issue_id = test_db.create_issue(
            risk_id='R001',
            title='Test Issue',
            description='Issue description',
            severity='Critical'
        )
        assert issue_id.startswith('ISS-')

    def test_get_issue(self, test_db, sample_issue):
        """Test retrieving an issue."""
        issue = test_db.get_issue(sample_issue)
        assert issue is not None
        assert issue['title'] == 'Sample Issue'
        assert issue['severity'] == 'High'

    def test_update_issue(self, test_db, sample_issue):
        """Test updating an issue."""
        test_db.update_issue(sample_issue, status='Resolved', assigned_to='Tester')
        issue = test_db.get_issue(sample_issue)
        assert issue['status'] == 'Resolved'
        assert issue['assigned_to'] == 'Tester'

    def test_get_all_issues(self, test_db, sample_risk):
        """Test getting all issues."""
        test_db.create_issue(risk_id='R001', title='Issue 1')
        test_db.create_issue(risk_id='R001', title='Issue 2')

        issues = test_db.get_all_issues()
        assert len(issues) == 2

    def test_issue_documentation(self, test_db, sample_issue):
        """Test saving/retrieving issue documentation."""
        test_db.save_issue_documentation(sample_issue, '<p>Test documentation</p>')
        issue = test_db.get_issue(sample_issue)
        assert issue['documentation'] == '<p>Test documentation</p>'


class TestDatabaseTasks:
    """Unit tests for kanban tasks database operations."""

    def test_add_task(self, test_db):
        """Test adding a task."""
        task_id = test_db.create_task(
            title='Test Task',
            description='Task description',
            priority='high',
            column_id='planning'
        )
        assert task_id is not None

    def test_get_task(self, test_db):
        """Test retrieving a task."""
        task_id = test_db.create_task(title='Test Task', priority='medium')
        task = test_db.get_task(task_id)
        assert task is not None
        assert task['title'] == 'Test Task'
        assert task['priority'] == 'medium'

    def test_update_task(self, test_db):
        """Test updating a task."""
        task_id = test_db.create_task(title='Original Title')
        test_db.update_task(task_id, title='Updated Title', column_id='testing')
        task = test_db.get_task(task_id)
        assert task['title'] == 'Updated Title'
        assert task['column_id'] == 'testing'

    def test_delete_task(self, test_db):
        """Test deleting a task."""
        task_id = test_db.create_task(title='To Delete')
        result = test_db.delete_task(task_id)
        assert result is True
        task = test_db.get_task(task_id)
        assert task is None

    def test_get_kanban_board(self, test_db):
        """Test getting kanban board structure."""
        test_db.create_task(title='Task 1', column_id='planning')
        test_db.create_task(title='Task 2', column_id='testing')

        board = test_db.get_kanban_format()
        assert 'boards' in board
        assert 'default' in board['boards']
        assert 'columns' in board['boards']['default']


class TestDatabaseFlowcharts:
    """Unit tests for flowcharts database operations."""

    def test_save_flowchart(self, test_db):
        """Test saving a flowchart."""
        data = {'drawflow': {'Home': {'data': {}}}}
        result = test_db.save_flowchart('test-flow', data)
        assert result  # Returns flowchart ID (int)

    def test_get_flowchart(self, test_db):
        """Test retrieving a flowchart."""
        data = {'drawflow': {'Home': {'data': {'node1': {}}}}}
        test_db.save_flowchart('test-flow', data)

        result = test_db.get_flowchart('test-flow')
        assert result is not None
        assert 'data' in result  # Data is stored under 'data' key
        assert 'drawflow' in result['data']

    def test_get_nonexistent_flowchart(self, test_db):
        """Test retrieving non-existent flowchart."""
        result = test_db.get_flowchart('nonexistent')
        assert result is None

    def test_list_flowcharts(self, test_db):
        """Test listing all flowcharts."""
        test_db.save_flowchart('flow1', {'data': 1})
        test_db.save_flowchart('flow2', {'data': 2})

        flowcharts = [f['name'] for f in test_db.get_all_flowcharts()]
        assert 'flow1' in flowcharts
        assert 'flow2' in flowcharts


class TestDatabaseTestDocuments:
    """Unit tests for test documents (DE/OE testing)."""

    def test_save_test_document(self, test_db, sample_risk):
        """Test saving a test document."""
        # Use risk_code version since we have risk_id as string
        result = test_db.save_test_document_by_risk_code('R001', 'de_testing', '<p>DE test content</p>')
        assert result is not None

    def test_get_test_document(self, test_db, sample_risk):
        """Test retrieving a test document."""
        test_db.save_test_document_by_risk_code('R001', 'de_testing', '<p>DE content</p>')

        doc = test_db.get_test_document_by_risk_code('R001', 'de_testing')
        assert doc is not None
        assert doc['content'] == '<p>DE content</p>'

    def test_test_document_exists(self, test_db, sample_risk):
        """Test checking if test document exists."""
        assert test_db.has_test_document('R001', 'de_testing') is False
        test_db.save_test_document_by_risk_code('R001', 'de_testing', 'content')
        assert test_db.has_test_document('R001', 'de_testing') is True


class TestDatabaseSQLQueries:
    """Unit tests for SQL query execution (AI tool)."""

    def test_execute_select_query(self, test_db, sample_risk):
        """Test executing valid SELECT query."""
        result = test_db.execute_query("SELECT * FROM risks WHERE risk_id = 'R001'")
        assert len(result) == 1
        assert result[0]['risk_id'] == 'R001'

    def test_reject_insert_query(self, test_db):
        """Test that INSERT queries are rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            test_db.execute_query("INSERT INTO risks (risk_id) VALUES ('BAD')")

    def test_reject_update_query(self, test_db):
        """Test that UPDATE queries are rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            test_db.execute_query("UPDATE risks SET status = 'bad'")

    def test_reject_delete_query(self, test_db):
        """Test that DELETE queries are rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            test_db.execute_query("DELETE FROM risks")

    def test_reject_drop_query(self, test_db):
        """Test that DROP queries are rejected."""
        with pytest.raises(ValueError, match="forbidden keyword"):
            test_db.execute_query("SELECT * FROM risks; DROP TABLE risks;--")

    def test_reject_multiple_statements(self, test_db):
        """Test that multiple statements are rejected."""
        with pytest.raises(ValueError, match="Multiple statements"):
            test_db.execute_query("SELECT 1; SELECT 2")


# ==================== UNIT TESTS: APP HELPERS ====================

class TestAppHelpers:
    """Unit tests for app.py helper functions."""

    def test_data_version_thread_safe(self):
        """Test thread-safe data version operations."""
        initial = app_module.get_data_version()
        new_version = app_module.increment_data_version()
        assert new_version == initial + 1
        assert app_module.get_data_version() == new_version

    def test_error_response_format(self, client):
        """Test standardized error response format."""
        # Access internal function
        with app_module.app.app_context():
            response, status = app_module.error_response('Test error', 400)
            data = response.get_json()
            assert data['error'] == 'Test error'
            assert status == 400

    def test_not_found_response(self, client):
        """Test 404 response format."""
        with app_module.app.app_context():
            response, status = app_module.not_found_response('Risk')
            data = response.get_json()
            assert 'Risk not found' in data['error']
            assert status == 404


# ==================== INTEGRATION TESTS: API ENDPOINTS ====================

class TestPageRoutes:
    """Integration tests for page routes."""

    def test_index_page(self, client):
        """Test RACM index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'RACM' in response.data

    def test_kanban_page(self, client):
        """Test Kanban page loads."""
        response = client.get('/kanban')
        assert response.status_code == 200
        assert b'Audit Plan' in response.data

    def test_flowchart_page(self, client):
        """Test Flowchart page loads."""
        response = client.get('/flowchart')
        assert response.status_code == 200

    def test_flowchart_page_with_id(self, client):
        """Test Flowchart page with specific ID."""
        response = client.get('/flowchart/test-flow')
        assert response.status_code == 200


class TestRACMAPI:
    """Integration tests for RACM API endpoints."""

    def test_get_data_returns_structure(self, client):
        """Test GET /api/data returns correct structure."""
        response = client.get('/api/data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'racm' in data
        assert 'issues' in data
        assert isinstance(data['racm'], list)
        assert isinstance(data['issues'], list)

    def test_post_data_saves_racm(self, client):
        """Test POST /api/data saves RACM data."""
        racm_data = {
            'racm': [
                ['R001', 'Test Risk', 'C001', 'Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']
            ],
            'issues': []
        }
        response = client.post('/api/data',
            data=json.dumps(racm_data),
            content_type='application/json')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['status'] == 'saved'

    def test_data_version_increments_on_save(self, client):
        """Test data version increments when data is saved."""
        initial_version = app_module.get_data_version()
        racm_data = {
            'racm': [['R999', 'Version Test', 'C999', 'Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']],
            'issues': []
        }
        client.post('/api/data', data=json.dumps(racm_data), content_type='application/json')
        # Version should have incremented
        assert app_module.get_data_version() > initial_version


class TestIssueAPI:
    """Integration tests for Issue Log API endpoints."""

    def test_create_issue_from_risk(self, client, test_db, sample_risk):
        """Test POST /api/issues/from-risk creates issue."""
        response = client.post('/api/issues/from-risk/R001')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'issue_id' in data
        assert data['issue_id'].startswith('ISS-')

    def test_get_issue(self, client, test_db, sample_issue):
        """Test GET /api/issues/{id} returns issue."""
        response = client.get(f'/api/issues/{sample_issue}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['issue_id'] == sample_issue

    def test_update_issue(self, client, test_db, sample_issue):
        """Test PUT /api/issues/{id} updates issue."""
        update_data = {'status': 'In Progress', 'assigned_to': 'Tester'}
        response = client.put(f'/api/issues/{sample_issue}',
            data=json.dumps(update_data),
            content_type='application/json')
        assert response.status_code == 200


class TestKanbanAPI:
    """Integration tests for Kanban API endpoints."""

    def test_get_default_board(self, client):
        """Test GET /api/kanban/default returns board."""
        response = client.get('/api/kanban/default')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'columns' in data

    def test_save_board(self, client):
        """Test POST /api/kanban/{name} saves board."""
        board_data = {
            'columns': [
                {'id': 'planning', 'title': 'Planning', 'items': []},
                {'id': 'testing', 'title': 'Testing', 'items': []}
            ]
        }
        response = client.post('/api/kanban/test-board',
            data=json.dumps(board_data),
            content_type='application/json')
        assert response.status_code == 200


class TestFlowchartAPI:
    """Integration tests for Flowchart API endpoints."""

    def test_list_flowcharts(self, client):
        """Test GET /api/flowcharts returns list."""
        # Create a flowchart via API
        flowchart_data = {'drawflow': {'Home': {'data': {}}}}
        client.post('/api/flowchart/api-test-flow', data=json.dumps(flowchart_data), content_type='application/json')

        response = client.get('/api/flowcharts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'api-test-flow' in data

    def test_save_flowchart(self, client):
        """Test POST /api/flowchart/{name} saves flowchart."""
        flowchart_data = {'drawflow': {'Home': {'data': {}}}}
        response = client.post('/api/flowchart/new-flow',
            data=json.dumps(flowchart_data),
            content_type='application/json')
        assert response.status_code == 200

    def test_get_flowchart(self, client, test_db):
        """Test GET /api/flowchart/{name} returns flowchart."""
        test_db.save_flowchart('get-test', {'drawflow': {}})
        response = client.get('/api/flowchart/get-test')
        assert response.status_code == 200


class TestTestDocumentAPI:
    """Integration tests for Test Document API endpoints."""

    def test_save_test_document(self, client, test_db, sample_risk):
        """Test POST /api/test-document saves document."""
        response = client.post('/api/test-document/R001/de_testing',
            data=json.dumps({'content': '<p>Test content</p>'}),
            content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'saved'

    def test_get_test_document(self, client, test_db, sample_risk):
        """Test GET /api/test-document returns document."""
        test_db.save_test_document_by_risk_code('R001', 'de_testing', '<p>Content</p>')
        response = client.get('/api/test-document/R001/de_testing')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['content'] == '<p>Content</p>'

    def test_test_document_exists(self, client, test_db, sample_risk):
        """Test GET /api/test-document/.../exists endpoint."""
        # First create via API to test full flow
        response = client.get('/api/test-document/R001/oe_testing/exists')
        assert response.status_code == 200
        data = json.loads(response.data)
        initial_exists = data['exists']

        # Save via API and check again
        client.post('/api/test-document/R001/oe_testing',
            data=json.dumps({'content': 'test content'}),
            content_type='application/json')
        response = client.get('/api/test-document/R001/oe_testing/exists')
        data = json.loads(response.data)
        assert data['exists'] is True


class TestChatAPI:
    """Integration tests for Chat API endpoints."""

    def test_chat_status(self, client):
        """Test GET /api/chat/status returns status."""
        response = client.get('/api/chat/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'configured' in data

    def test_chat_requires_message(self, client):
        """Test POST /api/chat handles empty request."""
        response = client.post('/api/chat',
            data=json.dumps({}),
            content_type='application/json')
        # Should handle gracefully
        assert response.status_code in [200, 400]


# ==================== UAT: USER ACCEPTANCE TESTS ====================

class TestUATRiskWorkflow:
    """UAT: Complete risk management workflow."""

    def test_full_risk_workflow(self, client, test_db):
        """Test complete workflow: add risk → test → review → close."""
        # 1. Add a risk via API
        racm_data = {
            'racm': [
                ['R100', 'UAT Test Risk', 'C100', 'UAT Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']
            ],
            'issues': []
        }
        response = client.post('/api/data',
            data=json.dumps(racm_data),
            content_type='application/json')
        assert response.status_code == 200

        # Verify risk was created
        risk = test_db.get_risk('R100')
        assert risk is not None, "Risk R100 should exist after saving"

        # 2. Add DE testing documentation
        response = client.post('/api/test-document/R100/de_testing',
            data=json.dumps({'content': '<p>DE testing performed. Control operates as designed.</p>'}),
            content_type='application/json')
        assert response.status_code == 200

        # 3. Add OE testing documentation
        response = client.post('/api/test-document/R100/oe_testing',
            data=json.dumps({'content': '<p>OE testing: 25 samples tested, all passed.</p>'}),
            content_type='application/json')
        assert response.status_code == 200

        # 4. Update risk status to Effective via spreadsheet save
        racm_data['racm'][0][8] = 'Effective'  # Status column
        racm_data['racm'][0][9] = True  # Ready for review
        response = client.post('/api/data',
            data=json.dumps(racm_data),
            content_type='application/json')
        assert response.status_code == 200

        risk = test_db.get_risk('R100')
        assert risk['status'] == 'Effective'

        # 5. Reviewer reviews and closes
        racm_data['racm'][0][10] = 'Senior Auditor'  # Reviewer
        racm_data['racm'][0][12] = True  # Closed
        response = client.post('/api/data',
            data=json.dumps(racm_data),
            content_type='application/json')
        assert response.status_code == 200

        risk = test_db.get_risk('R100')
        assert risk['reviewer'] == 'Senior Auditor'
        assert risk['closed'] == 1


class TestUATIssueWorkflow:
    """UAT: Complete issue management workflow."""

    def test_full_issue_workflow(self, client, test_db, sample_risk):
        """Test workflow: raise issue → assign → resolve → close."""
        # 1. Create issue from risk
        response = client.post('/api/issues/from-risk/R001')
        assert response.status_code == 200
        data = json.loads(response.data)
        issue_id = data['issue_id']

        # Verify issue was created
        issue = test_db.get_issue(issue_id)
        assert issue is not None, f"Issue {issue_id} should exist after creation"

        # 2. Update issue with details
        update_data = {
            'title': 'Control Gap Identified',
            'description': 'Monthly reconciliation not performed for 3 months',
            'severity': 'High',
            'status': 'Open',
            'assigned_to': 'Control Owner'
        }
        response = client.put(f'/api/issues/{issue_id}',
            data=json.dumps(update_data),
            content_type='application/json')
        assert response.status_code == 200

        # 3. Add documentation
        response = client.post(f'/api/issues/{issue_id}/documentation',
            data=json.dumps({'documentation': '<p>Root cause: Staff turnover. Remediation: Training completed.</p>'}),
            content_type='application/json')
        assert response.status_code == 200

        # 4. Move to In Progress
        response = client.put(f'/api/issues/{issue_id}',
            data=json.dumps({'status': 'In Progress'}),
            content_type='application/json')
        assert response.status_code == 200

        # 5. Resolve and close
        response = client.put(f'/api/issues/{issue_id}',
            data=json.dumps({'status': 'Closed'}),
            content_type='application/json')
        assert response.status_code == 200

        # Verify final state via API
        response = client.get(f'/api/issues/{issue_id}')
        data = json.loads(response.data)
        assert data['status'] == 'Closed'


class TestUATKanbanWorkflow:
    """UAT: Complete kanban task workflow."""

    def test_full_kanban_workflow(self, client, test_db, sample_risk):
        """Test workflow: create task → move through columns → complete."""
        # 1. Create task via database
        task_id = test_db.create_task(
            title='Perform walkthrough for R001',
            description='Document the process flow',
            priority='high',
            column_id='planning'
        )
        assert task_id is not None

        # 2. Move to Testing
        test_db.update_task(task_id, column_id='testing')
        task = test_db.get_task(task_id)
        assert task['column_id'] == 'testing'

        # 3. Move to Review
        test_db.update_task(task_id, column_id='review')
        task = test_db.get_task(task_id)
        assert task['column_id'] == 'review'

        # 4. Complete
        test_db.update_task(task_id, column_id='complete')
        task = test_db.get_task(task_id)
        assert task['column_id'] == 'complete'

        # 5. Verify in board structure
        board = test_db.get_kanban_format()
        assert 'boards' in board
        default_board = board['boards'].get('default', {})
        columns = default_board.get('columns', [])
        complete_col = next((c for c in columns if c['id'] == 'complete'), None)
        assert complete_col is not None


class TestUATFlowchartWorkflow:
    """UAT: Complete flowchart workflow."""

    def test_full_flowchart_workflow(self, client, test_db, sample_risk):
        """Test workflow: create → edit → link to risk."""
        # 1. Create flowchart
        flowchart_data = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {
                            'id': 1,
                            'name': 'start',
                            'data': {'name': 'Start'},
                            'pos_x': 100,
                            'pos_y': 100
                        },
                        '2': {
                            'id': 2,
                            'name': 'process',
                            'data': {'name': 'Review Documents'},
                            'pos_x': 300,
                            'pos_y': 100
                        },
                        '3': {
                            'id': 3,
                            'name': 'end',
                            'data': {'name': 'Complete'},
                            'pos_x': 500,
                            'pos_y': 100
                        }
                    }
                }
            }
        }
        response = client.post('/api/flowchart/uat-process-flow',
            data=json.dumps(flowchart_data),
            content_type='application/json')
        assert response.status_code == 200

        # 2. Retrieve and verify
        response = client.get('/api/flowchart/uat-process-flow')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'drawflow' in data

        # 3. Update flowchart
        flowchart_data['drawflow']['Home']['data']['4'] = {
            'id': 4,
            'name': 'decision',
            'data': {'name': 'Approve?'},
            'pos_x': 400,
            'pos_y': 200
        }
        response = client.post('/api/flowchart/uat-process-flow',
            data=json.dumps(flowchart_data),
            content_type='application/json')
        assert response.status_code == 200

        # 4. Verify in list
        response = client.get('/api/flowcharts')
        data = json.loads(response.data)
        assert 'uat-process-flow' in data


class TestUATDataIntegrity:
    """UAT: Data integrity across operations."""

    def test_concurrent_saves(self, client, test_db):
        """Test data integrity with multiple saves."""
        # Save multiple times rapidly
        for i in range(5):
            racm_data = {
                'racm': [
                    [f'R{i:03d}', f'Risk {i}', f'C{i:03d}', 'Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']
                ],
                'issues': []
            }
            response = client.post('/api/data',
                data=json.dumps(racm_data),
                content_type='application/json')
            assert response.status_code == 200

    def test_special_characters_handling(self, client, test_db):
        """Test handling of special characters in data."""
        racm_data = {
            'racm': [
                ['R001', "Risk with 'quotes' and \"double quotes\"", 'C001', "O'Brien", '', '', '', '', 'Not Complete', False, '', False, False, '', '', ''],
                ['R002', 'Risk with <html> & special chars', 'C002', 'Owner', '', '', '', '', 'Not Complete', False, '', False, False, '', '', '']
            ],
            'issues': []
        }
        response = client.post('/api/data',
            data=json.dumps(racm_data),
            content_type='application/json')
        assert response.status_code == 200

        # Verify data saved correctly
        response = client.get('/api/data')
        data = json.loads(response.data)
        assert any("O'Brien" in str(row) for row in data['racm'])


# ==================== EDGE CASES & ERROR HANDLING ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_data_save(self, client):
        """Test saving empty data."""
        response = client.post('/api/data',
            data=json.dumps({'racm': [], 'issues': []}),
            content_type='application/json')
        assert response.status_code == 200

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/data',
            data='not valid json',
            content_type='application/json')
        assert response.status_code in [400, 500]

    def test_missing_content_type(self, client):
        """Test handling of missing content type."""
        response = client.post('/api/data',
            data='{}')
        # Should still work or return appropriate error
        assert response.status_code in [200, 400, 415]

    def test_nonexistent_issue(self, client):
        """Test accessing non-existent issue."""
        response = client.get('/api/issues/NONEXISTENT-999')
        assert response.status_code == 404

    def test_invalid_risk_for_issue(self, client, test_db):
        """Test creating issue for non-existent risk."""
        response = client.post('/api/issues/from-risk/NONEXISTENT')
        # Should handle gracefully
        assert response.status_code in [200, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
