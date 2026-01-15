"""
Authentication and Authorization Module for SmartPapers

Provides decorators for protecting Flask routes:
- @require_login: Ensures user is authenticated
- @require_admin: Ensures user is an admin
- @require_audit_access: Ensures user has access to the specified audit
"""

from functools import wraps
from flask import session, redirect, url_for, request, jsonify, g
from database import get_db


def get_current_user():
    """Get the current logged-in user from session.

    Returns user dict with: id, email, name, is_admin, is_active
    Returns None if not logged in.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None

    # Cache user in g for the request
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user

    db = get_db()
    user = db.get_user_by_id(user_id)

    if user:
        # Don't expose password_hash
        user_safe = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'is_admin': bool(user['is_admin']),
            'is_active': bool(user['is_active'])
        }
        g.current_user = user_safe
        return user_safe

    return None


def require_login(f):
    """Decorator that requires the user to be logged in.

    For page routes: redirects to /login if not authenticated.
    For API routes (starting with /api/): returns 401 JSON response.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))

        if not user['is_active']:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Account is deactivated'}), 403
            return redirect(url_for('login', error='account_deactivated'))

        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator that requires the user to be an admin.

    Returns 403 Forbidden if not an admin.
    Must be used after @require_login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))

        if not user['is_admin']:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            return "Access denied. Admin privileges required.", 403

        return f(*args, **kwargs)
    return decorated_function


def require_audit_access(min_role='viewer'):
    """Decorator factory that requires the user to have access to an audit.

    The audit_id must be:
    - In the URL parameters (e.g., /audit/<audit_id>/...)
    - In the request JSON body as 'audit_id'
    - In the query string as 'audit_id'
    - In the session as 'active_audit_id'

    Role hierarchy (lower number = higher permission):
    - admin (1): Full access
    - auditor (2): Can edit assigned audits
    - reviewer (3): Can read and add comments
    - viewer (4): Read-only access

    Args:
        min_role: Minimum role required (default: 'viewer')

    Usage:
        @app.route('/audit/<int:audit_id>/risks')
        @require_login
        @require_audit_access('auditor')
        def get_audit_risks(audit_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login', next=request.url))

            # Admins have access to everything
            if user['is_admin']:
                return f(*args, **kwargs)

            # Find audit_id from various sources
            audit_id = None

            # 1. Check URL parameters
            if 'audit_id' in kwargs:
                audit_id = kwargs['audit_id']

            # 2. Check request JSON body
            if not audit_id and request.is_json:
                data = request.get_json(silent=True) or {}
                audit_id = data.get('audit_id')

            # 3. Check query string
            if not audit_id:
                audit_id = request.args.get('audit_id', type=int)

            # 4. Check session for active audit
            if not audit_id:
                audit_id = session.get('active_audit_id')

            if not audit_id:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'No audit specified'}), 400
                return "No audit specified", 400

            # Check membership
            db = get_db()
            if not db.user_has_audit_access(user['id'], audit_id, min_role):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Access denied to this audit'}), 403
                return "Access denied to this audit", 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_active_audit_id():
    """Get the currently active audit ID from session.

    Returns None if no audit is selected.
    """
    return session.get('active_audit_id')


def set_active_audit(audit_id):
    """Set the active audit in the session.

    Verifies the user has access before setting.
    Returns True if successful, False if no access.
    """
    user = get_current_user()
    if not user:
        return False

    # Admins can access any audit
    if user['is_admin']:
        session['active_audit_id'] = audit_id
        return True

    # Check membership
    db = get_db()
    if db.user_has_audit_access(user['id'], audit_id, 'viewer'):
        session['active_audit_id'] = audit_id
        return True

    return False


def get_user_accessible_audits():
    """Get list of audits the current user can access.

    Returns empty list if not logged in.
    """
    user = get_current_user()
    if not user:
        return []

    db = get_db()
    return db.get_accessible_audits(user['id'], user['is_admin'])


def login_user(user_id, email, name, is_admin):
    """Set session variables for a logged-in user."""
    session['user_id'] = user_id
    session['user_email'] = email
    session['user_name'] = name
    session['is_admin'] = bool(is_admin)


def logout_user():
    """Clear all session data."""
    session.clear()


def check_password(password, password_hash):
    """Verify a password against its hash."""
    from werkzeug.security import check_password_hash
    return check_password_hash(password_hash, password)


def hash_password(password):
    """Hash a password for storage."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='pbkdf2:sha256')
