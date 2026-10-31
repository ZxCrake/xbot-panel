"""Security helpers: rate limiter, response headers, and input validation."""
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from . import settings
from .files import profile_path
from .proxies import SESSION_FORMATS, parse_proxy_list, validate_proxy_line

# Shared limiter instance (initialised against the app in create_app).
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATELIMIT_STORAGE_URI,
    default_limits=["600 per hour", "60 per minute"],
)


def apply_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # All scripts are served from /static; inline handlers are forbidden.
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; object-src 'none'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    if settings.BEHIND_PROXY and request.is_secure:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


def apply_cors(resp):
    """Token (not cookie) auth → CSRF-safe. CORS only if a front origin is set."""
    origin = settings.FRONTEND_ORIGIN
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        resp.headers["Vary"] = "Origin"
    return resp


# ── Input validation for bot config ─────────────────────────────────────────

_INT_BOUNDS = {
    "threads": (1, settings.MAX_THREADS_PER_USER),
    "limit": (1, 1000),
    "select_users": (0, 50),
    "mentions_per_target": (1, 50),
    "delay_min": (0, 3600),
    "delay_max": (0, 3600),
    "account_delay_min": (0, 86400),
    "account_delay_max": (0, 86400),
    "proxy_session_epoch": (0, 1_000_000_000),
}
_STR_FIELDS = {"proxy": 256, "proxies": 65536, "proxy_mode": 16,
               "proxy_session_format": 16,
               "pfp_image": 128, "display_name": 100, "bio": 320}
_BOOL_FIELDS = {"follow_mentioned", "random_mention_position"}
_PROXY_MODES = ("static", "rotating")


def validate_config(raw: dict) -> dict:
    """Coerce + bound-check a user-supplied config dict. Raises ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("config must be an object")
    out = {}
    for key in _BOOL_FIELDS:
        if key in raw:
            out[key] = 1 if raw[key] in (1, "1", True, "true", "on", "yes") else 0
    for key, (lo, hi) in _INT_BOUNDS.items():
        if key in raw and raw[key] != "":
            try:
                v = int(raw[key])
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be an integer")
            if not (lo <= v <= hi):
                raise ValueError(f"{key} must be between {lo} and {hi}")
            out[key] = v
    for key, maxlen in _STR_FIELDS.items():
        if key in raw and raw[key] is not None:
            v = str(raw[key])
            if len(v) > maxlen:
                raise ValueError(f"{key} too long (max {maxlen})")
            out[key] = v
    if "proxy_mode" in out and out["proxy_mode"] not in _PROXY_MODES:
        raise ValueError("proxy_mode must be 'static' or 'rotating'")
    if "proxy_session_format" in out and out["proxy_session_format"] not in SESSION_FORMATS:
        raise ValueError("proxy_session_format must be 'auto', 'generic' or 'dataimpulse'")
    # Chaque ligne de proxies doit être une URL de proxy valide, sinon la
    # résolution tomberait silencieusement sur le fallback (connexion directe
    # non désirée par l'opérateur) — échouer tôt et visiblement.
    if "proxies" in out:
        try:
            parse_proxy_list(out["proxies"])
        except ValueError as e:
            raise ValueError(f"proxies: {e}")
    if "proxy" in out and out["proxy"].strip():
        validate_proxy_line(out["proxy"].strip())
    if "pfp_image" in out:
        profile_path(settings.USER_DATA_ROOT, out["pfp_image"])
    return out
