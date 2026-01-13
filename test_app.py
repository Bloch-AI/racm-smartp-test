"""
Regression tests for RACM Audit Toolkit
Run with: pytest test_app.py -v
"""
import pytest
import json
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create test client"""
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_data():
    """Reset data before each test"""
    # Store original data
    original_spreadsheet = [row[:] for row in app_module.spreadsheet_data]
    original_kanban = json.loads(json.dumps(app_module.kanban_data))
    original_flowcharts = dict(app_module.flowchart_data)
    original_version = app_module.data_version

    yield

    # Restore original data after test
    app_module.spreadsheet_data.clear()
    app_module.spreadsheet_data.extend(original_spreadsheet)
    app_module.kanban_data.clear()
    app_module.kanban_data.update(original_kanban)
    app_module.flowchart_data.clear()
    app_module.flowchart_data.update(original_flowcharts)
    app_module.data_version = original_version


class TestHealthAndPages:
    """Test page routes return 200"""

    def test_index_page(self, client):
        """Test RACM index page loads"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'RACM' in response.data

    def test_kanban_page(self, client):
        """Test Kanban page loads"""
        response = client.get('/kanban')
        assert response.status_code == 200
        assert b'Audit Plan' in response.data

    def test_flowchart_page(self, client):
        """Test Flowchart page loads"""
        response = client.get('/flowchart')
        assert response.status_code == 200
        assert b'Flowchart' in response.data

    def test_flowchart_page_with_id(self, client):
        """Test Flowchart page loads with specific flowchart ID"""
        response = client.get('/flowchart/test-flow')
        assert response.status_code == 200


class TestRACMAPI:
    """Test RACM spreadsheet API endpoints"""

    def test_get_data(self, client):
        """Test GET /api/data returns spreadsheet data"""
        response = client.get('/api/data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
        # Check header row
        assert data[0][0] == 'Risk ID'
        assert data[0][1] == 'Risk Description'

    def test_post_data(self, client):
        """Test POST /api/data updates spreadsheet"""
        new_data = [
            ['Risk ID', 'Risk Description', 'Control Description', 'Control Owner', 'Frequency', 'Status', 'Flowchart', 'Task'],
            ['R001', 'Test Risk', 'Test Control', 'Test Owner', 'Monthly', 'Effective', '', '']
        ]
        response = client.post('/api/data',
            data=json.dumps(new_data),
            content_type='application/json')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['status'] == 'saved'

        # Verify data was saved
        response = client.get('/api/data')
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[1][0] == 'R001'

    def test_data_integrity(self, client):
        """Test data maintains structure after save"""
        # Get original data
        response = client.get('/api/data')
        original_data = json.loads(response.data)

        # Modify and save
        original_data.append(['R999', 'New Risk', 'New Control', 'Owner', 'Daily', 'Not Tested', '', ''])
        client.post('/api/data',
            data=json.dumps(original_data),
            content_type='application/json')

        # Verify structure
        response = client.get('/api/data')
        data = json.loads(response.data)
        assert len(data) == len(original_data)
        assert data[-1][0] == 'R999'


class TestKanbanAPI:
    """Test Kanban board API endpoints"""

    def test_get_default_board(self, client):
        """Test GET /api/kanban/default returns board"""
        response = client.get('/api/kanban/default')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'columns' in data
        assert isinstance(data['columns'], list)

    def test_create_board(self, client):
        """Test POST /api/kanban creates new board"""
        board_data = {
            'columns': [
                {'id': 'todo', 'title': 'To Do', 'items': []},
                {'id': 'done', 'title': 'Done', 'items': []}
            ]
        }
        response = client.post('/api/kanban/test-board',
            data=json.dumps(board_data),
            content_type='application/json')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['status'] == 'saved'

        # Verify board was created
        response = client.get('/api/kanban/test-board')
        data = json.loads(response.data)
        assert len(data['columns']) == 2

    def test_get_nonexistent_board_returns_null(self, client):
        """Test GET returns null for nonexistent board"""
        response = client.get('/api/kanban/nonexistent-board-xyz')
        assert response.status_code == 200
        # API returns null for nonexistent boards
        data = response.get_json()
        assert data is None or data == {} or 'columns' not in data or data.get('columns') is None

    def test_get_task(self, client):
        """Test GET /api/kanban/{board}/task/{id}"""
        # First create a board with a task
        board_data = {
            'columns': [{
                'id': 'todo',
                'title': 'To Do',
                'items': [{
                    'id': 'task-123',
                    'title': 'Test Task',
                    'description': 'Test Description',
                    'priority': 'high'
                }]
            }]
        }
        client.post('/api/kanban/task-test-board',
            data=json.dumps(board_data),
            content_type='application/json')

        # Get the task
        response = client.get('/api/kanban/task-test-board/task/task-123')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Test Task'
        assert data['priority'] == 'high'

    def test_update_task(self, client):
        """Test PUT /api/kanban/{board}/task/{id}"""
        # Create board with task that has all required fields
        board_data = {
            'columns': [{
                'id': 'todo',
                'title': 'To Do',
                'items': [{'id': 'task-456', 'title': 'Original', 'description': '', 'priority': 'medium', 'assignee': '', 'dueDate': '', 'riskId': ''}]
            }]
        }
        client.post('/api/kanban/update-test-board',
            data=json.dumps(board_data),
            content_type='application/json')

        # Update task
        update_data = {'title': 'Updated Title', 'description': 'New desc', 'priority': 'low'}
        response = client.put('/api/kanban/update-test-board/task/task-456',
            data=json.dumps(update_data),
            content_type='application/json')
        assert response.status_code == 200

        # Verify update
        response = client.get('/api/kanban/update-test-board/task/task-456')
        data = json.loads(response.data)
        assert data['title'] == 'Updated Title'


class TestFlowchartAPI:
    """Test Flowchart API endpoints"""

    def test_list_flowcharts(self, client):
        """Test GET /api/flowcharts returns list"""
        response = client.get('/api/flowcharts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_save_flowchart(self, client):
        """Test POST /api/flowchart/{name} saves flowchart"""
        flowchart_data = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {
                            'id': 1,
                            'name': 'start',
                            'data': {'name': 'Start'},
                            'class': 'start',
                            'html': '<div>Start</div>',
                            'inputs': {},
                            'outputs': {'output_1': {'connections': []}},
                            'pos_x': 100,
                            'pos_y': 100
                        }
                    }
                }
            }
        }
        response = client.post('/api/flowchart/test-flowchart',
            data=json.dumps(flowchart_data),
            content_type='application/json')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['status'] == 'saved'

        # Verify in list
        response = client.get('/api/flowcharts')
        data = json.loads(response.data)
        assert 'test-flowchart' in data

    def test_get_flowchart(self, client):
        """Test GET /api/flowchart/{name} returns flowchart"""
        # Save first
        flowchart_data = {'drawflow': {'Home': {'data': {}}}}
        client.post('/api/flowchart/get-test',
            data=json.dumps(flowchart_data),
            content_type='application/json')

        # Get
        response = client.get('/api/flowchart/get-test')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'drawflow' in data

    def test_get_nonexistent_flowchart_returns_null(self, client):
        """Test GET returns null for nonexistent flowchart"""
        response = client.get('/api/flowchart/nonexistent-xyz')
        assert response.status_code == 200
        # API returns null for nonexistent flowcharts
        data = response.get_json()
        assert data is None


class TestChatAPI:
    """Test Chat API endpoints (without hitting real AI)"""

    def test_chat_status_configured(self, client):
        """Test GET /api/chat/status when API key is set"""
        response = client.get('/api/chat/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'configured' in data

    def test_chat_requires_message(self, client):
        """Test POST /api/chat requires message"""
        response = client.post('/api/chat',
            data=json.dumps({}),
            content_type='application/json')
        # Should still return 200 but with error or empty response
        assert response.status_code == 200


class TestToolExecution:
    """Test AI tool execution functions directly"""

    def test_add_racm_row_tool(self, client):
        """Test add_racm_row tool execution"""
        result = app_module.execute_tool('add_racm_row', {
            'risk_id': 'R999',
            'risk_description': 'Test Risk',
            'control_description': 'Test Control',
            'control_owner': 'Test Owner',
            'frequency': 'Monthly',
            'status': 'Not Tested'
        })

        assert 'R999' in result
        assert 'added' in result.lower() or 'success' in result.lower()

        # Verify row was added
        response = client.get('/api/data')
        data = json.loads(response.data)
        risk_ids = [row[0] for row in data]
        assert 'R999' in risk_ids

    def test_update_racm_status_tool(self, client):
        """Test update_racm_status tool execution"""
        result = app_module.execute_tool('update_racm_status', {
            'risk_id': 'R001',
            'new_status': 'Ineffective'
        })

        assert 'R001' in result or 'updated' in result.lower()

        # Verify status was updated
        response = client.get('/api/data')
        data = json.loads(response.data)
        r001_row = next((row for row in data if row[0] == 'R001'), None)
        assert r001_row is not None
        assert r001_row[5] == 'Ineffective'

    def test_create_kanban_task_tool(self, client):
        """Test create_kanban_task tool execution"""
        result = app_module.execute_tool('create_kanban_task', {
            'title': 'Test Task from Tool',
            'description': 'Created by test',
            'column': 'planning',
            'priority': 'high'
        })

        assert 'created' in result.lower() or 'task' in result.lower() or 'success' in result.lower()

    def test_create_kanban_task_with_risk_link(self, client):
        """Test create_kanban_task links to RACM row"""
        result = app_module.execute_tool('create_kanban_task', {
            'title': 'Linked Task',
            'description': 'Should link to R001',
            'column': 'testing',
            'risk_id': 'R001'
        })

        assert 'linked' in result.lower() or 'R001' in result

        # Verify link in RACM
        r001_row = next((row for row in app_module.spreadsheet_data if row[0] == 'R001'), None)
        assert r001_row[7] != ''  # Task column should be set

    def test_create_flowchart_tool(self, client):
        """Test create_flowchart tool execution"""
        result = app_module.execute_tool('create_flowchart', {
            'name': 'tool-test-flowchart',
            'steps': [
                {'type': 'start', 'name': 'Begin'},
                {'type': 'process', 'name': 'Step 1'},
                {'type': 'end', 'name': 'Finish'}
            ]
        })

        assert 'created' in result.lower() or 'flowchart' in result.lower() or 'success' in result.lower()

        # Verify flowchart exists
        response = client.get('/api/flowcharts')
        data = json.loads(response.data)
        assert 'tool-test-flowchart' in data

    def test_create_flowchart_with_risk_link(self, client):
        """Test create_flowchart links to RACM row"""
        result = app_module.execute_tool('create_flowchart', {
            'name': 'linked-flowchart',
            'steps': [{'type': 'start', 'name': 'Start'}],
            'risk_id': 'R002'
        })

        # Verify link in RACM
        r002_row = next((row for row in app_module.spreadsheet_data if row[0] == 'R002'), None)
        assert r002_row[6] == 'linked-flowchart'  # Flowchart column

    def test_get_audit_summary_tool(self, client):
        """Test get_audit_summary tool execution"""
        result = app_module.execute_tool('get_audit_summary', {})

        # Result is JSON string
        summary = json.loads(result)
        assert 'racm_rows' in summary
        assert 'status_breakdown' in summary
        assert 'total_tasks' in summary


class TestDataVersion:
    """Test data versioning for frontend refresh"""

    def test_data_version_increments_on_tool_use(self, client):
        """Test data_version increments when tool modifies data"""
        initial_version = app_module.data_version

        # Use add_racm_row tool which should increment version
        app_module.execute_tool('add_racm_row', {
            'risk_id': 'R888',
            'risk_description': 'Version Test',
            'control_description': 'Control',
            'control_owner': 'Owner',
            'frequency': 'Daily',
            'status': 'Effective'
        })

        assert app_module.data_version > initial_version


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_spreadsheet_data(self, client):
        """Test handling empty spreadsheet save"""
        response = client.post('/api/data',
            data=json.dumps([]),
            content_type='application/json')
        assert response.status_code == 200

    def test_special_characters_in_flowchart_name(self, client):
        """Test flowchart names with special characters"""
        flowchart_data = {'drawflow': {'Home': {'data': {}}}}
        response = client.post('/api/flowchart/test%20flow%20chart',
            data=json.dumps(flowchart_data),
            content_type='application/json')
        assert response.status_code == 200

    def test_large_kanban_board(self, client):
        """Test saving board with many tasks"""
        items = [{'id': f'task-{i}', 'title': f'Task {i}', 'description': '', 'priority': 'medium'}
                 for i in range(100)]
        board_data = {
            'columns': [{'id': 'large', 'title': 'Large Column', 'items': items}]
        }
        response = client.post('/api/kanban/large-board',
            data=json.dumps(board_data),
            content_type='application/json')
        assert response.status_code == 200

        # Verify all tasks saved
        response = client.get('/api/kanban/large-board')
        data = json.loads(response.data)
        assert len(data['columns'][0]['items']) == 100

    def test_unknown_tool_returns_error(self, client):
        """Test unknown tool name returns error message"""
        result = app_module.execute_tool('nonexistent_tool', {})
        assert 'unknown' in result.lower() or result is None or result == ''


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
