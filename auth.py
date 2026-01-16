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


def require_non_viewer(f):
    """Decorator that blocks viewer role from write/modify operations.

    Viewers have read-only access - they cannot modify data or use AI features.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))

        user_role = get_user_role(user)
        if user_role == 'viewer':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'View only - viewers cannot modify data'}), 403
            return "Access denied. Viewers have read-only access.", 403

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

    # Global auditors can access any audit
    user_role = get_user_role(user)
    if user_role == 'auditor':
        session['active_audit_id'] = audit_id
        return True

    # Viewers need explicit assignment (via audit_team or audit_viewers)
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
    user_role = get_user_role(user)
    return db.get_accessible_audits(user['id'], user['is_admin'], user_role)


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


# ==================== WORKFLOW PERMISSION FUNCTIONS ====================

def get_user_role(user):
    """Get the user's role from the database (not from session).

    Returns: 'admin', 'auditor', 'reviewer', 'viewer'
    """
    if not user:
        return None

    # Admin takes precedence (for backward compatibility with is_admin flag)
    if user.get('is_admin'):
        return 'admin'

    # Get role from user record if present
    db = get_db()
    full_user = db.get_user_by_id(user['id'])
    if full_user:
        return full_user.get('role') or 'viewer'

    return 'viewer'


def can_view_audit(user, audit):
    """Check if user can view an audit.

    Permission model:
    - Admins: can view all audits
    - Auditors/Reviewers: can view ALL audits (full visibility)
    - Viewers: can ONLY view audits specifically assigned to them
    """
    if not user or not audit:
        return False

    # Admin can view all
    if user.get('is_admin'):
        return True

    user_id = user['id']
    audit_id = audit['id'] if isinstance(audit, dict) else audit
    user_role = get_user_role(user)

    # Auditors can view ALL audits (reviewer global role consolidated into auditor)
    if user_role == 'auditor':
        return True

    # Viewers can ONLY view audits they're explicitly assigned to
    if user_role == 'viewer':
        db = get_db()
        return db.is_viewer_of_audit(user_id, audit_id)

    return False


def can_edit_record(user, audit, record):
    """Check if user can edit a specific record based on its workflow status.

    Edit permission depends on:
    - Record status (draft, in_review, admin_hold, signed_off)
    - User assignment to audit team (via audit_team junction table)
    - For in_review: must be THE reviewer assigned to this specific record

    Returns True if user can edit the record.
    """
    if not user or not audit or not record:
        return False

    # Admin cannot directly edit - must unlock first if needed
    # (Admin uses separate override endpoints)

    record_status = record.get('record_status') or 'draft'

    # Signed-off and admin_hold records cannot be edited
    if record_status in ('signed_off', 'admin_hold'):
        return False

    user_id = user['id']
    audit_id = audit['id'] if isinstance(audit, dict) else audit
    db = get_db()

    # Draft records: ANY assigned auditor can edit
    if record_status == 'draft':
        return db.is_auditor_on_audit(user_id, audit_id)

    # In-review records: ONLY the assigned reviewer for this record can edit
    if record_status == 'in_review':
        # Must be the specific reviewer who was assigned this record
        assigned_reviewer_id = record.get('assigned_reviewer_id')
        if assigned_reviewer_id and assigned_reviewer_id == user_id:
            # Verify they're still a reviewer on the audit
            return db.is_reviewer_on_audit(user_id, audit_id)
        return False

    return False


def can_transition_record(user, audit, record, action):
    """Check if user can perform a specific state transition.

    Actions:
    - submit_for_review: ANY assigned auditor submits draft -> in_review
    - return_to_auditor: THE assigned reviewer returns in_review -> draft
    - sign_off: THE assigned reviewer signs off in_review -> signed_off
    - admin_lock: admin locks any -> admin_hold
    - admin_unlock: admin unlocks admin_hold -> draft/in_review
    - admin_unlock_signoff: admin unlocks signed_off -> draft/in_review

    Returns True if the transition is allowed.
    """
    if not user or not audit or not record:
        return False

    record_status = record.get('record_status') or 'draft'
    user_id = user['id']
    user_role = get_user_role(user)
    audit_id = audit['id'] if isinstance(audit, dict) else audit
    db = get_db()

    # Get the assigned reviewer for this record (for in_review transitions)
    assigned_reviewer_id = record.get('assigned_reviewer_id')

    transitions = {
        'submit_for_review': lambda: (
            record_status == 'draft' and
            db.is_auditor_on_audit(user_id, audit_id)
        ),
        'return_to_auditor': lambda: (
            record_status == 'in_review' and
            assigned_reviewer_id == user_id and
            db.is_reviewer_on_audit(user_id, audit_id)
        ),
        'sign_off': lambda: (
            record_status == 'in_review' and
            assigned_reviewer_id == user_id and
            db.is_reviewer_on_audit(user_id, audit_id)
        ),
        'admin_lock': lambda: (
            user_role == 'admin' and
            record_status not in ('admin_hold',)
        ),
        'admin_unlock': lambda: (
            user_role == 'admin' and
            record_status == 'admin_hold'
        ),
        'admin_unlock_signoff': lambda: (
            user_role == 'admin' and
            record_status == 'signed_off'
        ),
    }

    check = transitions.get(action)
    return check() if check else False


def get_record_permissions(user, audit, record):
    """Get all permissions for a record in one call.

    Returns a dict with boolean flags for each permission.
    Useful for client-side rendering of action buttons.
    """
    if not user or not audit or not record:
        return {
            'canView': False,
            'canEdit': False,
            'canSubmitForReview': False,
            'canReturnToAuditor': False,
            'canSignOff': False,
            'canAdminLock': False,
            'canAdminUnlock': False,
            'canAdminUnlockSignoff': False
        }

    return {
        'canView': can_view_audit(user, audit),
        'canEdit': can_edit_record(user, audit, record),
        'canSubmitForReview': can_transition_record(user, audit, record, 'submit_for_review'),
        'canReturnToAuditor': can_transition_record(user, audit, record, 'return_to_auditor'),
        'canSignOff': can_transition_record(user, audit, record, 'sign_off'),
        'canAdminLock': can_transition_record(user, audit, record, 'admin_lock'),
        'canAdminUnlock': can_transition_record(user, audit, record, 'admin_unlock'),
        'canAdminUnlockSignoff': can_transition_record(user, audit, record, 'admin_unlock_signoff')
    }


# ==================== RECORD PERMISSION DECORATOR ====================

def require_record_edit(record_type):
    """Decorator that checks if user can edit the specified record.

    Usage:
        @app.route('/api/risks/<int:record_id>', methods=['PUT'])
        @require_login
        @require_record_edit('risk')
        def update_risk(record_id):
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

            # Get record_id from kwargs
            record_id = kwargs.get('record_id') or kwargs.get('risk_id') or kwargs.get('issue_id')
            if not record_id:
                return jsonify({'error': 'Record ID required'}), 400

            db = get_db()
            record = db.get_record_with_audit(record_type, record_id)
            if not record:
                return jsonify({'error': 'Record not found'}), 404

            # Build audit dict from record data
            audit = {
                'id': record.get('audit_id'),
                'auditor_id': record.get('auditor_id'),
                'reviewer_id': record.get('reviewer_id')
            }

            if not can_edit_record(user, audit, record):
                return jsonify({'error': 'Cannot edit record in current state'}), 403

            # Store record and audit in g for the handler to use
            g.record = record
            g.audit = audit

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_transition(record_type, action):
    """Decorator that checks if user can perform a state transition.

    Usage:
        @app.route('/api/records/risk/<int:record_id>/submit-for-review', methods=['POST'])
        @require_login
        @require_transition('risk', 'submit_for_review')
        def submit_risk_for_review(record_id):
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

            # Get record_id from kwargs
            record_id = kwargs.get('record_id') or kwargs.get('risk_id') or kwargs.get('issue_id')
            if not record_id:
                return jsonify({'error': 'Record ID required'}), 400

            db = get_db()
            record = db.get_record_with_audit(record_type, record_id)
            if not record:
                return jsonify({'error': 'Record not found'}), 404

            # Build audit dict from record data
            audit = {
                'id': record.get('audit_id'),
                'auditor_id': record.get('auditor_id'),
                'reviewer_id': record.get('reviewer_id')
            }

            if not can_transition_record(user, audit, record, action):
                return jsonify({'error': f'Cannot perform {action} on this record'}), 403

            # Store record and audit in g for the handler to use
            g.record = record
            g.audit = audit

            return f(*args, **kwargs)
        return decorated_function
    return decorator
