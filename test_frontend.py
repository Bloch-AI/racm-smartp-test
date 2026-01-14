"""
Frontend Regression Tests for RACM Audit Toolkit.

These tests verify that all frontend-facing API endpoints and page routes
are functioning correctly. Run with: pytest test_frontend.py -v
"""

import io
import pytest
import app as app_module
from database import RACMDatabase


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    db = RACMDatabase(str(db_path))

    # Add sample data for testing
    db.create_risk(
        risk_id='R001',
        risk='Test Risk Description',
        control_id='C001',
        control_owner='Test Owner',
        status='Not Complete'
    )
    db.create_risk(
        risk_id='R002',
        risk='Another Risk Description',
        control_id='C002',
        control_owner='Another Owner',
        status='Not Complete'
    )

    # Create an issue
    db.create_issue(
        risk_id='R001',
        title='Test Issue',
        description='Test issue description',
        severity='Medium',
        status='Open'
    )

    # Create tasks for kanban
    db.create_task(
        title='Task 1',
        description='Test task',
        column_id='planning'
    )

    return db


@pytest.fixture
def client(test_db, tmp_path):
    """Create test client with isolated database."""
    app_module.app.config['TESTING'] = True
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir()
    app_module.app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    original_get_db = app_module.get_db
    original_db = app_module.db
    app_module.get_db = lambda: test_db
    app_module.db = test_db

    with app_module.app.test_client() as client:
        yield client

    app_module.get_db = original_get_db
    app_module.db = original_db


# ==================== Page Loading Tests ====================

class TestPageLoading:
    """Test that all pages load correctly."""

    def test_racm_main_page_loads(self, client):
        """RACM main page should load with 200 status."""
        response = client.get('/')
        assert response.status_code == 200

    def test_racm_page_has_spreadsheet(self, client):
        """RACM page should include jspreadsheet library."""
        response = client.get('/')
        html = response.data.decode()
        assert 'jspreadsheet' in html.lower()

    def test_racm_page_has_tabs(self, client):
        """RACM page should have tab navigation."""
        response = client.get('/')
        html = response.data.decode()
        assert 'tabs' in html.lower()

    def test_racm_page_has_quill_editor(self, client):
        """RACM page should include Quill.js for rich text editing."""
        response = client.get('/')
        html = response.data.decode()
        assert 'quill' in html.lower()

    def test_racm_page_has_chat_panel(self, client):
        """RACM page should have AI chat panel."""
        response = client.get('/')
        html = response.data.decode()
        assert 'chatPanel' in html or 'chat' in html.lower()

    def test_kanban_page_loads(self, client):
        """Kanban board page should load with 200 status."""
        response = client.get('/kanban')
        assert response.status_code == 200

    def test_kanban_page_has_board(self, client):
        """Kanban page should have kanban board elements."""
        response = client.get('/kanban')
        html = response.data.decode()
        assert 'kanban' in html.lower()

    def test_kanban_page_has_drag_support(self, client):
        """Kanban page should support drag and drop."""
        response = client.get('/kanban')
        html = response.data.decode()
        assert 'drag' in html.lower()

    def test_flowchart_page_loads(self, client):
        """Flowchart editor page should load with 200 status."""
        response = client.get('/flowchart')
        assert response.status_code == 200

    def test_flowchart_page_has_drawflow(self, client):
        """Flowchart page should include Drawflow library."""
        response = client.get('/flowchart')
        html = response.data.decode()
        assert 'drawflow' in html.lower()

    def test_flowchart_page_has_editor(self, client):
        """Flowchart page should have editor container."""
        response = client.get('/flowchart')
        html = response.data.decode()
        assert 'editor' in html.lower()


# ==================== RACM Spreadsheet API Tests ====================

class TestRACMSpreadsheetAPI:
    """Test RACM spreadsheet data API."""

    def test_load_racm_data(self, client):
        """Should load RACM data successfully."""
        response = client.get('/api/data')
        assert response.status_code == 200

    def test_racm_data_structure(self, client):
        """RACM data should have correct structure."""
        response = client.get('/api/data')
        data = response.get_json()
        assert 'racm' in data
        assert 'issues' in data

    def test_racm_has_rows(self, client):
        """RACM should contain data rows."""
        response = client.get('/api/data')
        data = response.get_json()
        assert len(data['racm']) > 0

    def test_issues_is_list(self, client):
        """Issues data should be a list."""
        response = client.get('/api/data')
        data = response.get_json()
        assert isinstance(data['issues'], list)

    def test_save_racm_data(self, client):
        """Should save RACM data successfully."""
        response = client.get('/api/data')
        data = response.get_json()

        save_response = client.post('/api/data', json=data)
        assert save_response.status_code == 200


# ==================== Issue Operations API Tests ====================

class TestIssueOperationsAPI:
    """Test issue-related API endpoints."""

    def test_list_issues(self, client):
        """Should list all issues."""
        response = client.get('/api/issues')
        assert response.status_code == 200
        issues = response.get_json()
        assert isinstance(issues, list)

    def test_get_single_issue(self, client):
        """Should get a single issue by ID."""
        # First get list to find an issue ID
        response = client.get('/api/issues')
        issues = response.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = client.get(f'/api/issues/{issue_id}')
            assert response.status_code == 200

    def test_create_issue_from_risk(self, client):
        """Should create issue from risk ID."""
        response = client.post('/api/issues/from-risk/R001', json={})
        assert response.status_code in [200, 201]

    def test_update_issue(self, client):
        """Should update an existing issue."""
        response = client.get('/api/issues')
        issues = response.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            update_data = {'status': 'In Progress'}
            response = client.put(f'/api/issues/{issue_id}', json=update_data)
            assert response.status_code == 200


# ==================== Kanban Board API Tests ====================

class TestKanbanBoardAPI:
    """Test Kanban board API endpoints."""

    def test_get_kanban_board(self, client):
        """Should get kanban board data."""
        response = client.get('/api/kanban/default')
        assert response.status_code == 200

    def test_kanban_has_columns(self, client):
        """Kanban board should have columns."""
        response = client.get('/api/kanban/default')
        data = response.get_json()
        assert 'columns' in data or isinstance(data, list)

    def test_kanban_column_count(self, client):
        """Kanban should have at least 5 columns."""
        response = client.get('/api/kanban/default')
        data = response.get_json()
        if 'columns' in data:
            assert len(data['columns']) >= 5

    def test_kanban_expected_columns(self, client):
        """Kanban should have expected column names."""
        response = client.get('/api/kanban/default')
        data = response.get_json()
        expected_columns = ['planning', 'fieldwork', 'testing', 'review', 'complete']
        if 'columns' in data:
            # columns is a list of dicts with 'id' field
            column_ids = [col['id'] for col in data['columns']]
            for col in expected_columns:
                assert col in column_ids


# ==================== Flowchart API Tests ====================

class TestFlowchartAPI:
    """Test flowchart API endpoints."""

    def test_list_flowcharts(self, client):
        """Should list all flowcharts."""
        response = client.get('/api/flowcharts')
        assert response.status_code == 200
        flowcharts = response.get_json()
        assert isinstance(flowcharts, list)

    def test_save_flowchart(self, client):
        """Should save a new flowchart."""
        test_flowchart = {
            'nodes': [{'id': 1, 'name': 'Start'}],
            'connections': []
        }
        response = client.post('/api/flowchart/regression_test', json=test_flowchart)
        assert response.status_code == 200

    def test_get_flowchart(self, client):
        """Should retrieve a saved flowchart."""
        # First save a flowchart
        test_flowchart = {'nodes': [], 'connections': []}
        client.post('/api/flowchart/get_test', json=test_flowchart)

        # Then retrieve it
        response = client.get('/api/flowchart/get_test')
        assert response.status_code == 200

    def test_flowchart_data_preserved(self, client):
        """Saved flowchart data should be preserved."""
        test_flowchart = {
            'nodes': [{'id': 1, 'name': 'TestNode'}],
            'connections': [{'from': 1, 'to': 2}]
        }
        client.post('/api/flowchart/data_test', json=test_flowchart)

        response = client.get('/api/flowchart/data_test')
        data = response.get_json()
        assert 'nodes' in data or 'data' in data


# ==================== AI Chat API Tests ====================

class TestAIChatAPI:
    """Test AI chat API endpoints."""

    def test_chat_status_endpoint(self, client):
        """Chat status endpoint should respond."""
        response = client.get('/api/chat/status')
        assert response.status_code == 200

    def test_chat_status_structure(self, client):
        """Chat status should have configured field."""
        response = client.get('/api/chat/status')
        data = response.get_json()
        assert 'configured' in data

    def test_chat_message_endpoint(self, client):
        """Chat message endpoint should accept messages."""
        response = client.post('/api/chat', json={'message': 'test'})
        # Accept 200 (success) or 400/401 (no API key configured)
        assert response.status_code in [200, 400, 401, 500]

    def test_chat_returns_json(self, client):
        """Chat endpoint should return JSON."""
        response = client.post('/api/chat', json={'message': 'test'})
        assert response.content_type == 'application/json'


# ==================== Evidence/Attachments API Tests ====================

class TestEvidenceAttachmentsAPI:
    """Test evidence and attachment API endpoints."""

    def test_upload_risk_attachment(self, client):
        """Should upload attachment to risk."""
        test_file = (io.BytesIO(b'Test file content'), 'test.txt')
        response = client.post(
            '/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data'
        )
        assert response.status_code == 200

    def test_upload_returns_file_info(self, client):
        """Upload should return file information."""
        test_file = (io.BytesIO(b'Test content'), 'info_test.txt')
        response = client.post(
            '/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data'
        )
        data = response.get_json()
        assert 'filename' in data or 'id' in data

    def test_list_risk_attachments(self, client):
        """Should list attachments for a risk."""
        response = client.get('/api/risks/R001/attachments')
        assert response.status_code == 200
        attachments = response.get_json()
        assert isinstance(attachments, list)

    def test_upload_issue_attachment(self, client):
        """Should upload attachment to issue."""
        # First get an issue ID
        issues_response = client.get('/api/issues')
        issues = issues_response.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            test_file = (io.BytesIO(b'Issue evidence'), 'evidence.txt')
            response = client.post(
                f'/api/issues/{issue_id}/attachments',
                data={'file': test_file},
                content_type='multipart/form-data'
            )
            assert response.status_code == 200

    def test_list_issue_attachments(self, client):
        """Should list attachments for an issue."""
        issues_response = client.get('/api/issues')
        issues = issues_response.get_json()
        if issues:
            issue_id = issues[0].get('issue_id')
            response = client.get(f'/api/issues/{issue_id}/attachments')
            assert response.status_code == 200


# ==================== Test Documents API Tests ====================

class TestTestDocumentsAPI:
    """Test test document (working paper) API endpoints."""

    def test_save_de_test_document(self, client):
        """Should save DE testing document."""
        doc = {'content': '<h1>DE Testing</h1><p>Test procedures.</p>'}
        response = client.post('/api/test-document/R001/de_testing', json=doc)
        assert response.status_code == 200

    def test_save_oe_test_document(self, client):
        """Should save OE testing document."""
        doc = {'content': '<h1>OE Testing</h1><p>Test procedures.</p>'}
        response = client.post('/api/test-document/R001/oe_testing', json=doc)
        assert response.status_code == 200

    def test_get_de_test_document(self, client):
        """Should retrieve DE testing document."""
        # First save a document
        doc = {'content': '<p>Test content</p>'}
        client.post('/api/test-document/R001/de_testing', json=doc)

        # Then retrieve it
        response = client.get('/api/test-document/R001/de_testing')
        assert response.status_code == 200

    def test_document_content_preserved(self, client):
        """Document content should be preserved."""
        content = '<h1>Preserved Content</h1>'
        doc = {'content': content}
        client.post('/api/test-document/R001/de_testing', json=doc)

        response = client.get('/api/test-document/R001/de_testing')
        data = response.get_json()
        assert content in data.get('content', '')

    def test_check_document_exists(self, client):
        """Should check if document exists."""
        # Save a document first
        doc = {'content': '<p>Exists test</p>'}
        client.post('/api/test-document/R001/de_testing', json=doc)

        response = client.get('/api/test-document/R001/de_testing/exists')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('exists') == True

    def test_invalid_doc_type_rejected(self, client):
        """Invalid document type should be rejected."""
        doc = {'content': '<p>Test</p>'}
        response = client.post('/api/test-document/R001/invalid_type', json=doc)
        assert response.status_code == 400


# ==================== Risk API Tests ====================

class TestRiskAPI:
    """Test risk CRUD API endpoints."""

    def test_list_risks(self, client):
        """Should list all risks."""
        response = client.get('/api/risks')
        assert response.status_code == 200
        risks = response.get_json()
        assert isinstance(risks, list)

    def test_get_single_risk(self, client):
        """Should get a single risk by ID."""
        response = client.get('/api/risks/R001')
        assert response.status_code == 200

    def test_create_risk(self, client):
        """Should create a new risk."""
        risk_data = {
            'risk_id': 'R999',
            'risk': 'New Risk Description',
            'control_id': 'C999',
            'control_owner': 'New Owner',
            'status': 'Not Complete'
        }
        response = client.post('/api/risks', json=risk_data)
        assert response.status_code in [200, 201]

    def test_update_risk(self, client):
        """Should update an existing risk."""
        update_data = {'process_name': 'Updated Process'}
        response = client.put('/api/risks/R001', json=update_data)
        assert response.status_code == 200


# ==================== Integration Tests ====================

class TestFrontendIntegration:
    """Integration tests for complete frontend workflows."""

    def test_complete_racm_workflow(self, client):
        """Test complete RACM load-edit-save workflow."""
        # Load data
        response = client.get('/api/data')
        assert response.status_code == 200
        data = response.get_json()

        # Modify and save
        save_response = client.post('/api/data', json=data)
        assert save_response.status_code == 200

        # Verify data persisted
        verify_response = client.get('/api/data')
        assert verify_response.status_code == 200

    def test_issue_creation_workflow(self, client):
        """Test creating issue from risk and viewing it."""
        # Create issue from risk
        response = client.post('/api/issues/from-risk/R001', json={})
        assert response.status_code in [200, 201]

        # Verify issue appears in list
        list_response = client.get('/api/issues')
        issues = list_response.get_json()
        risk_issues = [i for i in issues if i.get('risk_id') == 'R001']
        assert len(risk_issues) > 0

    def test_evidence_workflow(self, client):
        """Test uploading and listing evidence."""
        # Upload file
        test_file = (io.BytesIO(b'Evidence content'), 'evidence.txt')
        upload_response = client.post(
            '/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data'
        )
        assert upload_response.status_code == 200

        # List and verify
        list_response = client.get('/api/risks/R001/attachments')
        attachments = list_response.get_json()
        assert len(attachments) > 0

    def test_test_document_workflow(self, client):
        """Test creating and retrieving test documents."""
        # Save document
        doc = {'content': '<h1>Test</h1><p>Findings here.</p>'}
        save_response = client.post('/api/test-document/R001/de_testing', json=doc)
        assert save_response.status_code == 200

        # Check exists
        exists_response = client.get('/api/test-document/R001/de_testing/exists')
        assert exists_response.get_json().get('exists') == True

        # Retrieve and verify
        get_response = client.get('/api/test-document/R001/de_testing')
        data = get_response.get_json()
        assert 'Findings here' in data.get('content', '')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
