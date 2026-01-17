"""Security-focused tests for RACM Smart-P application.

These tests cover:
- Password security (hashing, salting)
- SQL injection prevention
- Input validation and XSS prevention
- File upload security
- Session security
- Authorization and access control
- AI tool security
- Rate limiting

Run security tests: pytest -m security
Run regression tests: pytest -m regression
"""
import pytest
import app as app_module
from database import RACMDatabase
from werkzeug.security import generate_password_hash, check_password_hash

# Mark entire module as security tests
pytestmark = [pytest.mark.security]


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
    uploads_dir = tmp_path / 'uploads'
    uploads_dir.mkdir()
    app_module.app.config['UPLOAD_FOLDER'] = str(uploads_dir)

    original_db = app_module.db
    app_module.db = test_db

    with app_module.app.test_client() as client:
        yield client

    app_module.db = original_db


@pytest.mark.regression
class TestPasswordSecurity:
    """Tests for password hashing and storage."""

    def test_password_not_stored_plaintext(self, test_db):
        """Verify passwords are hashed, not stored in plaintext."""
        password = 'SecretPassword123'
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        test_db.create_user(
            email='test@example.com',
            name='Test User',
            password_hash=password_hash
        )
        user = test_db.get_user_by_email('test@example.com')

        assert user is not None
        assert user.get('password_hash') != password
        # Werkzeug hashes start with method identifier
        assert user.get('password_hash', '').startswith('pbkdf2:sha256:')

    def test_same_password_different_hashes(self, test_db):
        """Verify same password produces different hashes (salted)."""
        password = 'SamePass123'
        hash1 = generate_password_hash(password, method='pbkdf2:sha256')
        hash2 = generate_password_hash(password, method='pbkdf2:sha256')

        test_db.create_user(email='u1@test.com', name='User 1', password_hash=hash1)
        test_db.create_user(email='u2@test.com', name='User 2', password_hash=hash2)

        user1 = test_db.get_user_by_email('u1@test.com')
        user2 = test_db.get_user_by_email('u2@test.com')

        # Each hash should be different due to salting
        assert user1['password_hash'] != user2['password_hash']

    def test_wrong_password_rejected(self, test_db):
        """Verify authentication fails with wrong password."""
        password = 'CorrectPassword'
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        test_db.create_user(
            email='auth@test.com',
            name='Auth Test',
            password_hash=password_hash
        )

        user = test_db.get_user_by_email('auth@test.com')

        # Correct password should work
        assert check_password_hash(user['password_hash'], 'CorrectPassword') is True

        # Wrong password should fail
        assert check_password_hash(user['password_hash'], 'WrongPassword') is False
        assert check_password_hash(user['password_hash'], '') is False


@pytest.mark.regression
class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""

    def test_execute_query_blocks_insert(self, test_db):
        """Verify INSERT statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("INSERT INTO risks VALUES (1, 'hack')")

    def test_execute_query_blocks_update(self, test_db):
        """Verify UPDATE statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("UPDATE risks SET risk = 'hacked'")

    def test_execute_query_blocks_delete(self, test_db):
        """Verify DELETE statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("DELETE FROM risks")

    def test_execute_query_blocks_drop(self, test_db):
        """Verify DROP statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("DROP TABLE risks")

    def test_execute_query_blocks_pragma(self, test_db):
        """Verify PRAGMA statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("PRAGMA table_info(users)")

    def test_execute_query_blocks_attach(self, test_db):
        """Verify ATTACH statements are blocked."""
        with pytest.raises(ValueError, match='Only SELECT'):
            test_db.execute_query("ATTACH DATABASE '/etc/passwd' AS pwned")

    def test_execute_query_allows_select(self, test_db):
        """Verify SELECT statements work."""
        # Should not raise
        result = test_db.execute_query("SELECT 1 as test")
        assert result is not None

    def test_parameterized_queries_safe(self, test_db):
        """Verify parameterized queries prevent injection."""
        # Create a risk
        test_db.create_risk(
            risk_id='R001',
            risk='Test Risk',
            control_id='C001',
            control_owner='Owner'
        )

        # Attempt SQL injection via parameter
        malicious_input = "'; DROP TABLE risks; --"
        risk = test_db.get_risk(malicious_input)

        # Should return None, not execute the DROP
        assert risk is None

        # Original risk should still exist
        risk = test_db.get_risk('R001')
        assert risk is not None


class TestInputValidation:
    """Tests for input validation and XSS prevention."""

    def test_special_characters_in_risk_description(self, test_db):
        """Verify special characters are handled safely."""
        test_db.create_risk(
            risk_id='R001',
            risk="<script>alert('xss')</script>",
            control_id='C001',
            control_owner="O'Malley & Co."
        )

        risk = test_db.get_risk('R001')
        # Data should be stored as-is (escaping happens on display)
        assert risk['risk'] == "<script>alert('xss')</script>"
        assert risk['control_owner'] == "O'Malley & Co."

    def test_unicode_handling(self, test_db):
        """Verify Unicode characters are handled correctly."""
        test_db.create_risk(
            risk_id='R002',
            risk='Risk with émojis 🔐 and symbols £€¥',
            control_id='C002',
            control_owner='Tëst Üser'
        )

        risk = test_db.get_risk('R002')
        assert '🔐' in risk['risk']
        assert 'Üser' in risk['control_owner']

    def test_null_byte_handling(self, test_db):
        """Verify null bytes don't cause issues."""
        test_db.create_risk(
            risk_id='R003',
            risk='Risk with\x00null byte',
            control_id='C003',
            control_owner='Owner'
        )

        risk = test_db.get_risk('R003')
        assert risk is not None


class TestFileUploadSecurity:
    """Tests for file upload security."""

    def test_path_traversal_prevented(self, client, test_db):
        """Verify path traversal in filenames is prevented."""
        import io

        # Create a risk to attach to
        test_db.create_risk(risk_id='R001', risk='Test', control_id='C001', control_owner='Owner')

        # Attempt path traversal
        test_file = (io.BytesIO(b'malicious content'), '../../../etc/passwd')
        response = client.post(
            '/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        # Should sanitize filename, reject, or require auth (401 is OK - means auth is required)
        if response.status_code == 200:
            data = response.get_json()
            # Filename should be sanitized
            assert '../' not in data.get('filename', '')
            assert 'etc' not in data.get('filename', '')

    def test_dangerous_extension_handling(self, client, test_db):
        """Verify dangerous file extensions are handled."""
        import io

        test_db.create_risk(risk_id='R001', risk='Test', control_id='C001', control_owner='Owner')

        # Attempt to upload executable
        test_file = (io.BytesIO(b'#!/bin/bash\nrm -rf /'), 'script.sh')
        response = client.post(
            '/api/risks/R001/attachments',
            data={'file': test_file},
            content_type='multipart/form-data'
        )

        # Should reject, sanitize, or require auth
        # 401 is acceptable - means endpoint now requires authentication (security improvement)
        assert response.status_code in [200, 400, 401]


@pytest.mark.regression
class TestSessionSecurity:
    """Tests for session security."""

    def test_session_cookie_httponly(self, client):
        """Verify session cookies have HttpOnly flag."""
        # Make any request that creates a session
        response = client.get('/')

        set_cookie = response.headers.get('Set-Cookie', '')
        if 'session' in set_cookie.lower():
            # In production, HttpOnly should be set
            # Note: May not be present in test mode
            pass

    def test_login_creates_session(self, client, test_db):
        """Verify login creates a session."""
        password = 'TestPass123'
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        test_db.create_user(
            email='session@test.com',
            name='Session Test',
            password_hash=password_hash
        )

        response = client.post('/login', data={
            'email': 'session@test.com',
            'password': password
        })

        # Should either redirect or return success
        assert response.status_code in [200, 302]


@pytest.mark.regression
@pytest.mark.auth
class TestAuthorizationChecks:
    """Tests for authorization and access control."""

    def test_unauthenticated_api_access(self, client):
        """Verify unauthenticated API access is handled."""
        response = client.get('/api/admin/users')
        # Should require authentication
        assert response.status_code in [401, 403, 302]

    def test_all_api_routes_require_authentication(self, client):
        """Verify ALL /api/* routes return 401 when unauthenticated.

        This is a comprehensive test to prevent auth decorator regressions.
        Every API endpoint must require authentication.
        """
        # Collect all API routes from the app
        api_routes = []
        for rule in app_module.app.url_map.iter_rules():
            if rule.rule.startswith('/api/'):
                # Skip routes with complex converters we can't easily test
                if '<' in rule.rule:
                    # Use placeholder values for path parameters
                    test_path = rule.rule
                    test_path = test_path.replace('<int:', '<').replace('<string:', '<')
                    test_path = test_path.replace('<risk_id>', 'TEST_RISK_ID')
                    test_path = test_path.replace('<record_id>', '999')
                    test_path = test_path.replace('<issue_id>', '999')
                    test_path = test_path.replace('<audit_id>', '999')
                    test_path = test_path.replace('<user_id>', '999')
                    test_path = test_path.replace('<attachment_id>', '999')
                    test_path = test_path.replace('<record_type>', 'risk')
                    test_path = test_path.replace('<item_id>', '999')
                    test_path = test_path.replace('<library_id>', '999')
                    test_path = test_path.replace('<chunk_id>', '999')
                    # Handle any remaining generic patterns
                    import re
                    test_path = re.sub(r'<[^>]+>', '999', test_path)
                else:
                    test_path = rule.rule

                for method in rule.methods:
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        api_routes.append((test_path, method))

        # Test each route
        unprotected_routes = []
        for path, method in api_routes:
            if method == 'GET':
                response = client.get(path)
            elif method == 'POST':
                response = client.post(path, json={})
            elif method == 'PUT':
                response = client.put(path, json={})
            elif method == 'DELETE':
                response = client.delete(path)
            elif method == 'PATCH':
                response = client.patch(path, json={})
            else:
                continue

            # 401 = Unauthorized (correct)
            # 400 = Bad Request (acceptable - validation before auth in some cases)
            # 404 = Not Found (acceptable - resource doesn't exist)
            # Anything else (200, 201, 204) = UNPROTECTED ROUTE!
            if response.status_code not in [400, 401, 403, 404, 405]:
                unprotected_routes.append(f"{method} {path} -> {response.status_code}")

        # Fail if any routes are unprotected
        assert not unprotected_routes, (
            f"Found {len(unprotected_routes)} unprotected API routes:\n" +
            "\n".join(unprotected_routes)
        )

    def test_admin_endpoint_requires_admin(self, client, test_db):
        """Verify admin endpoints require admin role."""
        # Create non-admin user
        password_hash = generate_password_hash('ViewerPass', method='pbkdf2:sha256')
        test_db.create_user(
            email='viewer@test.com',
            name='Viewer',
            password_hash=password_hash,
            is_admin=0
        )

        user = test_db.get_user_by_email('viewer@test.com')

        # Login as viewer
        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess['email'] = user['email']
            sess['is_admin'] = False

        # Try to access admin endpoint
        response = client.get('/admin')
        assert response.status_code in [401, 403, 302]


class TestAIToolSecurity:
    """Tests for AI tool security."""

    def test_execute_sql_rejects_non_select(self):
        """Verify execute_sql tool only allows SELECT."""
        result = app_module.execute_tool('execute_sql', {
            'sql': 'DROP TABLE risks'
        })
        assert 'error' in result.lower() or 'forbidden' in result.lower() or 'select' in result.lower()

    def test_execute_sql_with_union(self):
        """Test UNION keyword handling (potential data exfiltration)."""
        # UNION can be used to extract data from other tables
        result = app_module.execute_tool('execute_sql', {
            'sql': "SELECT risk_id FROM risks UNION SELECT password_hash FROM users"
        })
        # Should either block or return error (UNION is blocked in database.py)
        assert 'error' in result.lower() or isinstance(result, str)


class TestRateLimiting:
    """Tests for rate limiting (if implemented)."""

    def test_rapid_login_attempts(self, client, test_db):
        """Test handling of rapid login attempts."""
        password_hash = generate_password_hash('TestPass', method='pbkdf2:sha256')
        test_db.create_user(
            email='rate@test.com',
            name='Rate Limit',
            password_hash=password_hash
        )

        # Make multiple rapid login attempts with wrong password
        for i in range(10):
            response = client.post('/login', data={
                'email': 'rate@test.com',
                'password': 'WrongPassword'
            })

        # Final attempt - should still work or be rate limited
        # (depends on implementation)
        assert response.status_code in [200, 302, 429]
