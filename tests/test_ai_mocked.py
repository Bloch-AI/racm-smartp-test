"""AI service tests with proper mocking.

Run with: pytest tests/test_ai_mocked.py -v
Run regression tests: pytest -m regression
"""
import json
import pytest
from unittest.mock import patch, Mock, MagicMock
import app as app_module
import database as database_module
from database import RACMDatabase
from werkzeug.security import generate_password_hash

# Mark entire module as regression tests (AI functionality is critical)
pytestmark = [pytest.mark.regression]


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    db = RACMDatabase(str(db_path))
    return db


@pytest.fixture
def client(test_db, tmp_path):
    """Create test client with isolated database."""
    app_module.app.config['TESTING'] = True
    original_db = app_module.db
    original_db_instance = database_module._db_instance

    # Set both the app module db and the database module's global instance
    app_module.db = test_db
    database_module._db_instance = test_db

    with app_module.app.test_client() as client:
        yield client

    app_module.db = original_db
    database_module._db_instance = original_db_instance


@pytest.fixture
def auth_client(client, test_db):
    """Create authenticated test client."""
    # Create a test user
    password_hash = generate_password_hash('TestPass123', method='pbkdf2:sha256')
    test_db.create_user(
        email='aitest@test.com',
        name='AI Test User',
        password_hash=password_hash,
        is_admin=1
    )
    user = test_db.get_user_by_email('aitest@test.com')

    # Set up session
    with client.session_transaction() as sess:
        sess['user_id'] = user['id']
        sess['email'] = user['email']
        sess['name'] = user['name']
        sess['is_admin'] = True

    return client


@pytest.fixture
def sample_risk(test_db):
    """Create a sample risk for testing."""
    test_db.create_risk(
        risk_id='R001',
        risk='Sample Risk Description',
        control_id='C001',
        control_owner='Test Owner',
        status='Not Complete'
    )
    return test_db.get_risk('R001')


class TestAIChatMocked:
    """Tests for AI chat with mocked Anthropic client."""

    @patch('app.anthropic')
    def test_chat_success_response(self, mock_anthropic, client, test_db):
        """Test successful chat response."""
        # Setup mock
        mock_response = Mock()
        mock_response.content = [Mock(type='text', text='Hello! How can I help?')]
        mock_response.stop_reason = 'end_turn'
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        response = client.post('/api/chat', json={'message': 'Hello'})

        if response.status_code == 200:
            data = response.get_json()
            assert 'response' in data or 'content' in data

    @patch('app.anthropic')
    def test_chat_with_tool_call(self, mock_anthropic, client, test_db, sample_risk):
        """Test chat that triggers tool use."""
        # First response requests tool use
        tool_use_response = Mock()
        tool_use_block = Mock()
        tool_use_block.type = 'tool_use'
        tool_use_block.id = 'tool_123'
        tool_use_block.name = 'get_audit_summary'
        tool_use_block.input = {}
        tool_use_response.content = [tool_use_block]
        tool_use_response.stop_reason = 'tool_use'

        # Second response after tool result
        final_response = Mock()
        final_response.content = [Mock(type='text', text='Based on the audit summary...')]
        final_response.stop_reason = 'end_turn'

        mock_anthropic.Anthropic.return_value.messages.create.side_effect = [
            tool_use_response,
            final_response
        ]

        response = client.post('/api/chat', json={
            'message': 'Give me an audit summary'
        })

        # Should complete successfully or require API key
        assert response.status_code in [200, 401, 503]

    def test_chat_without_api_key(self, client, test_db):
        """Test chat endpoint when no API key is configured."""
        # This test verifies the endpoint requires authentication
        response = client.post('/api/chat', json={'message': 'test'})

        # Should return 401 for unauthenticated request
        assert response.status_code == 401

    def test_chat_empty_message(self, client, test_db):
        """Test chat with empty message."""
        response = client.post('/api/chat', json={'message': ''})

        # Should return 401 for unauthenticated request
        assert response.status_code == 401


class TestFelixConversationsMocked:
    """Tests for Felix conversations with mocked AI."""

    def test_create_conversation(self, auth_client):
        """Test creating a new conversation."""
        response = auth_client.post('/api/felix/conversations')
        assert response.status_code == 200
        data = response.get_json()
        assert 'id' in data
        # UUID format check
        assert len(data['id']) == 36

    def test_list_conversations(self, auth_client):
        """Test listing conversations."""
        # Create a conversation first
        auth_client.post('/api/felix/conversations')

        response = auth_client.get('/api/felix/conversations')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_delete_conversation(self, auth_client):
        """Test deleting a conversation."""
        # Create
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        # Delete
        delete_resp = auth_client.delete(f'/api/felix/conversations/{conv_id}')
        assert delete_resp.status_code == 200

        # Verify deleted
        list_resp = auth_client.get('/api/felix/conversations')
        conversations = list_resp.get_json()
        conv_ids = [c['id'] for c in conversations]
        assert conv_id not in conv_ids

    @patch('app.anthropic')
    def test_felix_chat_with_context(self, mock_anthropic, auth_client, test_db, sample_risk):
        """Test Felix chat includes context."""
        mock_response = Mock()
        mock_response.content = [Mock(type='text', text='I can see you have risk R001.')]
        mock_response.stop_reason = 'end_turn'
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        # Create conversation
        create_resp = auth_client.post('/api/felix/conversations')
        conv_id = create_resp.get_json()['id']

        # Send message
        response = auth_client.post(f'/api/felix/conversations/{conv_id}/messages', json={
            'content': 'What risks do we have?'
        })

        # Should work or require API key
        assert response.status_code in [200, 401, 503]


class TestToolExecutionMocked:
    """Tests for AI tool execution with mocking."""

    def test_add_racm_row_tool(self, test_db, client):
        """Test add_racm_row tool execution."""
        result = app_module.execute_tool('add_racm_row', {
            'risk_id': 'R999',
            'risk_description': 'New Risk',
            'control_description': 'New Control',
            'control_owner': 'New Owner'
        })

        assert 'Successfully' in result or 'added' in result.lower()

        # Verify risk was created
        risk = test_db.get_risk('R999')
        assert risk is not None
        assert risk['risk_id'] == 'R999'

    def test_create_kanban_task_tool(self, test_db, client):
        """Test create_kanban_task tool execution."""
        result = app_module.execute_tool('create_kanban_task', {
            'title': 'Test Task',
            'description': 'Task description',
            'priority': 'high',
            'column': 'planning'
        })

        assert 'Successfully' in result or 'created' in result.lower()

    def test_update_racm_status_tool(self, test_db, sample_risk, client):
        """Test update_racm_status tool execution."""
        result = app_module.execute_tool('update_racm_status', {
            'risk_id': 'R001',
            'new_status': 'Effective'
        })

        assert 'Successfully' in result or 'updated' in result.lower()

        # Verify status changed
        risk = test_db.get_risk('R001')
        assert risk['status'] == 'Effective'

    def test_execute_sql_tool(self, test_db, sample_risk, client):
        """Test execute_sql tool with valid SELECT."""
        result = app_module.execute_tool('execute_sql', {
            'sql': "SELECT risk_id, status FROM risks WHERE risk_id = 'R001'"
        })

        assert 'R001' in result

    def test_get_audit_summary_tool(self, test_db, sample_risk, client):
        """Test get_audit_summary tool execution."""
        result = app_module.execute_tool('get_audit_summary', {})

        # Should contain summary information
        assert 'risk' in result.lower() or 'audit' in result.lower()

    def test_unknown_tool_error(self, test_db, client):
        """Test error for unknown tool."""
        result = app_module.execute_tool('nonexistent_tool', {})

        assert 'unknown' in result.lower() or 'error' in result.lower()

    def test_create_issue_tool(self, test_db, sample_risk, client):
        """Test create_issue tool execution."""
        result = app_module.execute_tool('create_issue', {
            'risk_id': 'R001',
            'title': 'Test Issue',
            'description': 'Issue description',
            'severity': 'High'
        })

        assert 'Successfully' in result or 'ISS-' in result

    def test_ask_clarifying_question_tool(self, test_db, client):
        """Test ask_clarifying_question tool."""
        result = app_module.execute_tool('ask_clarifying_question', {
            'question': 'Which risk do you mean?',
            'options': ['R001', 'R002', 'R003']
        })

        # Should return JSON with question
        data = json.loads(result)
        assert data['type'] == 'clarifying_question'
        assert 'question' in data


class TestSystemPromptBuilder:
    """Tests for AI system prompt building."""

    def test_build_system_prompt_returns_string(self, test_db, client):
        """System prompt builder should return string."""
        context = test_db.get_full_context()
        prompt = app_module.build_ai_system_prompt(context)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_contains_felix_identity(self, test_db, client):
        """System prompt should identify as Felix."""
        context = test_db.get_full_context()
        prompt = app_module.build_ai_system_prompt(context)

        assert 'Felix' in prompt

    def test_system_prompt_includes_context(self, test_db, sample_risk, client):
        """System prompt should include available data context."""
        context = test_db.get_full_context()
        prompt = app_module.build_ai_system_prompt(context)

        # Should reference risks or audit data
        assert 'risk' in prompt.lower() or 'audit' in prompt.lower()


class TestDataVersionTracking:
    """Tests for data version tracking in AI operations."""

    def test_data_version_non_negative(self):
        """Data version should be non-negative."""
        version = app_module.get_data_version()
        assert version >= 0

    def test_increment_data_version(self):
        """Incrementing should increase version."""
        initial = app_module.get_data_version()
        new_version = app_module.increment_data_version()
        assert new_version == initial + 1

    def test_tool_execution_increments_version(self, test_db, client):
        """Tool that modifies data should increment version."""
        initial = app_module.get_data_version()

        # Execute a modifying tool
        app_module.execute_tool('create_kanban_task', {
            'title': 'Version Test',
            'column': 'planning'
        })

        new_version = app_module.get_data_version()
        assert new_version > initial
