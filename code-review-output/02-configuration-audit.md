# Phase 1: Configuration & Secrets Audit

**Review Date:** 2026-01-15
**Reviewer:** Claude Code Review Agent

## Configuration Files Reviewed

| File | Purpose | Status |
|------|---------|--------|
| `.env` | Environment variables | CRITICAL ISSUES |
| `.gitignore` | Git exclusions | ACCEPTABLE |
| `app.py` (config section) | App configuration | NEEDS REVIEW |

## Environment Variables

### .env Contents Analysis

```
FLASK_APP=run.py                    # Note: run.py doesn't exist, app.py is main
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
ANTHROPIC_API_KEY=sk-ant-api03-... # LIVE API KEY EXPOSED
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads
```

### Expected Environment Variables

| Variable | Default | Used | Notes |
|----------|---------|------|-------|
| `SECRET_KEY` | `smartpapers-dev-key-change-in-production` | Yes | Hardcoded fallback in app.py |
| `ANTHROPIC_API_KEY` | Empty string | Yes | Required for AI features |
| `ADMIN_EMAIL` | `admin@localhost` | Yes | Default admin bootstrap |
| `ADMIN_PASSWORD` | `changeme123` | Yes | Default admin password |
| `DATABASE_URL` | None | No | Commented out in .env |

## Security Findings

### CRITICAL

#### CRT-001: API Key Exposed in .env File
**File:** `.env`
**Line:** 10
**Severity:** CRITICAL

The `.env` file contains a live Anthropic API key (`sk-ant-api03-...`). While `.env` is listed in `.gitignore`, the key may have been:
1. Committed to git history before gitignore was added
2. Copied to backups or shared environments
3. Exposed in error logs or stack traces

**Remediation:**
1. Immediately rotate the API key in Anthropic dashboard
2. Check git history: `git log --all --full-history -- .env`
3. If found in history, use `git filter-branch` or BFG to remove
4. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault) for production

### HIGH

#### HGH-001: Weak Default Secret Key
**File:** `app.py`
**Line:** 138
**Severity:** HIGH

```python
app.secret_key = os.environ.get('SECRET_KEY', 'smartpapers-dev-key-change-in-production')
```

The fallback secret key is predictable and static. If `SECRET_KEY` is not set in production, all sessions are signed with this known key.

**Remediation:**
```python
import secrets
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise ValueError("SECRET_KEY environment variable is required")
app.secret_key = secret_key
```

#### HGH-002: Default Admin Credentials
**File:** `database.py`
**Lines:** 320-337
**Severity:** HIGH

Default admin bootstrapped with predictable credentials:
- Email: `admin@localhost`
- Password: `changeme123`

While a warning is logged, the application doesn't enforce password change on first login.

**Remediation:**
1. Require password change on first admin login
2. Generate random initial password and display once
3. Add password complexity requirements

### MEDIUM

#### MED-001: Debug Mode Enabled
**File:** `.env`
**Line:** 3
**Severity:** MEDIUM

```
FLASK_ENV=development
```

Running with development mode enables:
- Detailed error pages with code exposure
- Werkzeug debugger (potential RCE if PIN is guessed)
- Auto-reload (minor information leakage)

**Remediation:** Ensure `FLASK_ENV=production` in production deployments

#### MED-002: Inconsistent Config Reference
**File:** `.env`
**Line:** 1
**Severity:** LOW

```
FLASK_APP=run.py
```

References `run.py` which doesn't exist. The actual entry point is `app.py`.

**Remediation:** Change to `FLASK_APP=app.py`

## .gitignore Analysis

### Currently Ignored
```
.env              # Good - secrets protected
*.db              # Good - database files excluded
__pycache__/      # Good - bytecode excluded
uploads/          # Good - user data excluded
library/          # Good - reference docs excluded
venv/             # Good - virtual env excluded
```

### Recommended Additions
```
.env.local
.env.*.local
*.log
*.bak
.coverage
htmlcov/
.pytest_cache/    # Already present
```

## Hardcoded Values in Source

| Value | Location | Concern |
|-------|----------|---------|
| `claude-sonnet-4-20250514` | app.py:14 | Model version hardcoded |
| `MAX_CHAT_HISTORY = 20` | app.py:15 | Not configurable |
| `50 * 1024 * 1024` | app.py:146 | 50MB limit hardcoded |
| `50000` | app.py:63,75,92,110 | Text extraction limits hardcoded |

## Recommendations

### Immediate Actions
1. **Rotate API key** - Consider the current key compromised
2. **Verify git history** - Ensure no secrets were committed
3. **Review production config** - Ensure SECRET_KEY is set securely

### Configuration Improvements
1. Create `config.py` with environment-specific settings:
   ```python
   class Config:
       SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-key'

   class ProductionConfig(Config):
       SECRET_KEY = os.environ.get('SECRET_KEY')
       if not SECRET_KEY:
           raise ValueError("SECRET_KEY required in production")
   ```

2. Add configuration validation at startup
3. Use pydantic-settings for type-safe configuration

### Secrets Management
For production deployment:
1. Use environment variables (not .env files)
2. Consider AWS Secrets Manager, HashiCorp Vault, or similar
3. Implement secrets rotation policy
