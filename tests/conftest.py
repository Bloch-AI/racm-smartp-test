"""Shared pytest fixtures for RACM Smart-P tests."""
import pytest
import app as app_module
from database import RACMDatabase


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app_module.app.config['TESTING'] = True
    app_module.app.config['WTF_CSRF_ENABLED'] = False
    return app_module.app


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with fresh schema."""
    db_path = tmp_path / "test.db"
    db = RACMDatabase(str(db_path))
    return db


@pytest.fixture
def client(app, test_db, tmp_path):
    """Create test client with isolated database."""
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    original_db = app_module.db
    app_module.db = test_db

    with app.test_client() as client:
        yield client

    app_module.db = original_db


@pytest.fixture
def auth_client(app, test_db, tmp_path):
    """Create authenticated test client."""
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    # Create test user
    from werkzeug.security import generate_password_hash
    test_db.create_user(
        email='test@example.com',
        name='Test User',
        password_hash=generate_password_hash('testpass123', method='pbkdf2:sha256'),
        is_admin=1
    )

    original_db = app_module.db
    app_module.db = test_db

    with app.test_client() as client:
        # Set up session
        with client.session_transaction() as sess:
            user = test_db.get_user_by_email('test@example.com')
            sess['user_id'] = user['id']
            sess['email'] = user['email']
            sess['name'] = user['name']
            sess['is_admin'] = user['is_admin']
        yield client

    app_module.db = original_db


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


@pytest.fixture
def sample_issue(test_db, sample_risk):
    """Create a sample issue for testing."""
    issue_id = test_db.create_issue(
        risk_id='R001',
        title='Sample Issue',
        description='Sample issue description',
        severity='Medium',
        status='Open'
    )
    return test_db.get_issue_by_id(issue_id)


@pytest.fixture
def sample_task(test_db):
    """Create a sample task for testing."""
    task_id = test_db.create_task(
        title='Sample Task',
        description='Sample task description',
        column_id='planning',
        priority='medium'
    )
    return test_db.get_task(task_id)


@pytest.fixture
def sample_flowchart(test_db):
    """Create a sample flowchart for testing."""
    flowchart_data = {
        'drawflow': {
            'Home': {
                'data': {
                    '1': {'id': 1, 'name': 'start', 'data': {'name': 'Start'}}
                }
            }
        }
    }
    test_db.save_flowchart('test-flowchart', flowchart_data)
    return test_db.get_flowchart('test-flowchart')


@pytest.fixture
def sample_library_document(test_db):
    """Create a sample library document for testing."""
    doc_id = test_db.add_library_document(
        name='Test Document',
        filename='test-doc.pdf',
        original_filename='Test Document.pdf',
        doc_type='standard',
        description='A test document'
    )

    # Add a chunk
    embedding = [0.1] * 384
    test_db.add_library_chunk(
        document_id=doc_id,
        chunk_index=0,
        content='This is test content for the library document.',
        embedding=embedding,
        section='Introduction'
    )

    return test_db.get_library_document(doc_id)


@pytest.fixture
def felix_conversation(test_db):
    """Create a sample Felix conversation for testing."""
    import uuid
    conv_id = str(uuid.uuid4())
    test_db.create_felix_conversation(conv_id, 'Test Conversation')
    return {'id': conv_id, 'title': 'Test Conversation'}


@pytest.fixture
def large_test_db(test_db):
    """Create a test database with many records for performance testing."""
    # Create 100 risks
    for i in range(100):
        test_db.create_risk(
            risk_id=f'R{i:03d}',
            risk=f'Risk {i} description',
            control_id=f'C{i:03d}',
            control_owner=f'Owner {i % 10}',
            status='Not Complete' if i % 3 == 0 else 'Effective'
        )

    # Create 50 tasks
    columns = ['planning', 'fieldwork', 'testing', 'review', 'complete']
    for i in range(50):
        test_db.create_task(
            title=f'Task {i}',
            description=f'Task {i} description',
            column_id=columns[i % 5],
            priority=['low', 'medium', 'high'][i % 3]
        )

    # Create 20 issues
    for i in range(20):
        test_db.create_issue(
            risk_id=f'R{i * 5:03d}',
            title=f'Issue {i}',
            description=f'Issue {i} description',
            severity=['Low', 'Medium', 'High', 'Critical'][i % 4],
            status=['Open', 'In Progress', 'Closed'][i % 3]
        )

    return test_db
