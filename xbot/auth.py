"""Authentication, authorization, and user management.

- Passwords hashed with Argon2id (argon2-cffi).
- Stateless signed tokens (itsdangerous) carrying a per-user token_version,
  so all of a user's sessions can be revoked by bumping the version.
- Brute-force protection: per-account failed-attempt counter + timed lockout.
- Role hierarchy: admin > moderator > user.
"""
import os
import re
import secrets
import datetime as dt
from functools import wraps

from flask import request, jsonify, g
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from . import settings
from .db import session, User
from .audit import log_action
from .files import workspace_path, safe_file

USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")
ROLE_RANK = {"user": 1, "moderator": 2, "admin": 3}

_ph = PasswordHasher()  # Argon2id with sane defaults
_dummy_hash = _ph.hash(secrets.token_urlsafe(32))

# Files seeded into a new user's working directory.
DEFAULT_FILES = {
    "accounts.txt": "",
    "users.txt": "",
    "tweets.txt": "[]",
    "reply.txt": "[]",
    "tweet_ids.txt": "",
    "emails.txt": "",
}


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _is_locked(u) -> bool:
    """Tz-safe lockout check (SQLite returns naive datetimes)."""
    if not u.locked_until:
        return False
    lu = u.locked_until
    if lu.tzinfo is None:
        lu = lu.replace(tzinfo=dt.timezone.utc)
    return lu > _utcnow()


# ── Per-user working directory ───────────────────────────────────────────────

def user_dir(username: str) -> str:
    u = get_user(username)
    if not u:
        raise ValueError("user not found")
    return workspace_path(settings.USER_DATA_ROOT, u.workspace_key)


def seed_user_dir(username: str):
    d = user_dir(username)
    os.makedirs(d, exist_ok=True)
    for name, content in DEFAULT_FILES.items():
        p = safe_file(d, name)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)


# ── Password validation ──────────────────────────────────────────────────────

def validate_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("username must be a string")
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise ValueError("invalid username (3-32 chars, a-z 0-9 _ - only)")
    return username


PASSWORD_MIN_LENGTH = max(1, min(64, int(os.environ.get("PASSWORD_MIN_LENGTH", "8") or "8")))


def validate_password(password: str):
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"password too short (min {PASSWORD_MIN_LENGTH} characters)")
    if len(password) > 128:
        raise ValueError("password too long (max 128 characters)")


# ── User management ──────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str = "user") -> str:
    username = validate_username(username)
    validate_password(password)
    role = role if role in ROLE_RANK else "user"
    s = session()
    if s.query(User).filter_by(username=username).first():
        raise ValueError("this user already exists")
    s.add(User(username=username, password_hash=_ph.hash(password), role=role))
    s.commit()
    seed_user_dir(username)
    log_action("user.create", username=username, detail=f"role={role}")
    return username


def delete_user(username: str) -> bool:
    username = (username or "").strip().lower()
    s = session()
    u = s.query(User).filter_by(username=username).first()
    if not u:
        return False
    # Revoke access before retiring the runner. Old requests retain the old
    # workspace identity and cannot access a later account with the same name.
    u.is_active = False
    u.token_version += 1
    s.commit()
    from .context import runners, runners_lock
    with runners_lock:
        runner = runners.pop(u.workspace_key, None)
        if runner:
            runner.retire()
    s.delete(u)
    s.commit()
    log_action("user.delete", username=username)
    return True


def set_password(username: str, password: str) -> bool:
    username = (username or "").strip().lower()
    validate_password(password)
    s = session()
    u = s.query(User).filter_by(username=username).first()
    if not u:
        return False
    u.password_hash = _ph.hash(password)
    u.token_version += 1  # revoke existing sessions
    s.commit()
    log_action("user.set_password", username=username)
    return True


def get_user(username: str) -> User | None:
    return session().query(User).filter_by(username=(username or "").strip().lower()).first()


def list_users() -> list[User]:
    return session().query(User).order_by(User.username).all()


def is_admin(username: str) -> bool:
    u = get_user(username)
    return bool(u and u.role == "admin")


# ── Authentication (with brute-force protection) ─────────────────────────────

def authenticate(username: str, password: str):
    """Return User on success, else None. Handles lockout + audit."""
    username = (username or "").strip().lower()
    s = session()
    u = s.query(User).filter_by(username=username).first()

    # Constant-ish behaviour: still run a hash check on a dummy when user missing,
    # to avoid trivial username enumeration via timing.
    if not u:
        try:
            _ph.verify(_dummy_hash, password)
        except Exception:
            pass
        log_action("login.fail", username=username, detail="no such user")
        return None

    if not u.is_active:
        log_action("login.fail", username=username, detail="inactive")
        return None

    if _is_locked(u):
        log_action("login.locked", username=username)
        return None

    try:
        _ph.verify(u.password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        u.failed_logins += 1
        if u.failed_logins >= settings.LOGIN_MAX_ATTEMPTS:
            u.locked_until = _utcnow() + dt.timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)
            u.failed_logins = 0
            log_action("login.lockout", username=username)
        else:
            log_action("login.fail", username=username, detail=f"attempt {u.failed_logins}")
        s.commit()
        return None

    # Success — reset counters, rehash if params changed, record login.
    u.failed_logins = 0
    u.locked_until = None
    u.last_login_at = _utcnow()
    if _ph.check_needs_rehash(u.password_hash):
        u.password_hash = _ph.hash(password)
    s.commit()
    log_action("login.ok", username=username)
    return u


def verify_user(username: str, password: str) -> bool:
    """Lightweight check without lockout side effects (used by tests/CLI)."""
    u = get_user(username)
    if not u:
        return False
    try:
        _ph.verify(u.password_hash, password)
        return True
    except Exception:
        return False


# ── Tokens (signed, stateless, revocable via token_version) ──────────────────

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="auth-token")


def generate_token(user: User) -> str:
    return _serializer().dumps({"u": user.username, "v": user.token_version,
                                "w": user.workspace_key})


def _user_from_token(token: str) -> User | None:
    try:
        data = _serializer().loads(token, max_age=settings.TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired, Exception):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("u"), str):
        return None
    u = get_user(data["u"])
    if (not u or not u.is_active or u.token_version != data.get("v")
            or u.workspace_key != data.get("w")):
        return None
    return u


def _bearer_user() -> User | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return _user_from_token(header[7:])
    return None


# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = _bearer_user()
        if not u:
            return jsonify({"error": "unauthorized"}), 401
        g.user = u.username
        g.role = u.role
        g.workspace_key = u.workspace_key
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    """Require one of the given roles (or higher, by rank)."""
    min_rank = min(ROLE_RANK[r] for r in roles)

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = _bearer_user()
            if not u:
                return jsonify({"error": "unauthorized"}), 401
            if ROLE_RANK.get(u.role, 0) < min_rank:
                return jsonify({"error": "forbidden"}), 403
            g.user = u.username
            g.role = u.role
            g.workspace_key = u.workspace_key
            return fn(*args, **kwargs)
        return wrapper
    return deco


def admin_required(fn):
    return roles_required("admin")(fn)
