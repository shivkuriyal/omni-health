"""
Utility helpers — password hashing, role decorators, OTP generation, audit logging.
"""

import bcrypt
import random
import string
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app import db


# ---------------------------------------------------------------------------
#  Password Hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ---------------------------------------------------------------------------
#  Role-Based Access Decorator
# ---------------------------------------------------------------------------
def role_required(*allowed_roles):
    """Decorator that restricts access to specific roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            identity = get_jwt_identity()
            if identity.get('role') not in allowed_roles:
                return jsonify({'error': 'Access denied — insufficient role'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
#  OTP Generation
# ---------------------------------------------------------------------------
# In-memory OTP store (use Redis in production)
_otp_store = {}


def generate_otp(consent_id: str, length: int = 6) -> str:
    """Generate a numeric OTP and store it with a 5-minute TTL."""
    otp = ''.join(random.choices(string.digits, k=length))
    _otp_store[consent_id] = {
        'otp': otp,
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
    }
    return otp


def verify_otp(consent_id: str, otp: str) -> bool:
    """Verify OTP against the store."""
    entry = _otp_store.get(consent_id)
    if not entry:
        return False
    if datetime.now(timezone.utc) > entry['expires_at']:
        _otp_store.pop(consent_id, None)
        return False
    if entry['otp'] != otp:
        return False
    _otp_store.pop(consent_id, None)
    return True


# ---------------------------------------------------------------------------
#  QR Token Generation
# ---------------------------------------------------------------------------
def generate_qr_token() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
#  Audit Logger
# ---------------------------------------------------------------------------
def log_audit(user_id, user_role, action, resource_type=None, resource_id=None, meta=None):
    """Write an entry to the audit log table."""
    from app.models import AuditLog
    entry = AuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=meta,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
    db.session.commit()
