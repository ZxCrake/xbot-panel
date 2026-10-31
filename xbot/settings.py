"""Centralized configuration, loaded from environment / .env.

All runtime configuration flows through this module. Nothing else should read
os.environ directly.
"""
import os
import secrets

from dotenv import load_dotenv

# Project root = parent of the xbot package
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env from the project root if present (no-op if absent)
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ── Environment ───────────────────────────────────────────────────────────────
ENV = os.getenv("XBOT_ENV", "production").strip().lower()
IS_PROD = ENV == "production"
DEBUG = not IS_PROD

# ── Filesystem ────────────────────────────────────────────────────────────────
DATA_ROOT = os.getenv("DATA_ROOT", os.path.join(BASE_DIR, "data"))
USER_DATA_ROOT = os.path.join(DATA_ROOT, "users")   # per-user bot working files
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")  # standalone CLI data
LOG_DIR = os.getenv("LOG_DIR", os.path.join(DATA_ROOT, "logs"))

os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(USER_DATA_ROOT, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ── Secret key (token signing) ──────────────────────────────────────────────
def _resolve_secret_key() -> str:
    key = os.getenv("SECRET_KEY", "").strip()
    if key:
        return key
    if IS_PROD:
        raise RuntimeError(
            "SECRET_KEY is required in production. "
            'Generate one: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    # Development convenience: persist a generated key so tokens survive restarts.
    path = os.path.join(DATA_ROOT, ".secret_key")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


SECRET_KEY = _resolve_secret_key()

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_ROOT, 'xbot.db')}")

# ── Auth / security ─────────────────────────────────────────────────────────
TOKEN_MAX_AGE = int(os.getenv("TOKEN_MAX_AGE", 60 * 60 * 24 * 7))  # 7 days
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", 5))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", 900))
BEHIND_PROXY = _bool("BEHIND_PROXY", False)

# ── Rate limiting ─────────────────────────────────────────────────────────────
RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Empty => same-origin only (no CORS headers emitted).
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").strip()

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

# ── X client (bot engine) ─────────────────────────────────────────────────────
XPFF_BASE_KEY = os.getenv(
    "XPFF_BASE_KEY",
    "0e6be1f1e21ffc33590b888fd4dc81b19713e570e805d4e5df80a493c9571a05",
)

# ── Application constants ─────────────────────────────────────────────────────
# Files a user may edit through the API (whitelist — prevents path traversal).
EDITABLE_FILES = {
    "accounts.txt",
    "tweets.txt",
    "reply.txt",
    "users.txt",
    "tweet_ids.txt",
    "dms.txt",
    "emails.txt",
}
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", 5 * 1024 * 1024))  # 5 MB per editable file
MAX_PFP_BYTES = int(os.getenv("MAX_PFP_BYTES", 8 * 1024 * 1024))    # 8 MB profile image
MAX_THREADS_PER_USER = max(1, int(os.getenv("MAX_THREADS_PER_USER", 10)))
MAX_ACTIVE_JOBS = max(1, int(os.getenv("MAX_ACTIVE_JOBS", 4)))
MAX_ACCOUNTS_PER_JOB = max(1, int(os.getenv("MAX_ACCOUNTS_PER_JOB", 1000)))
X_REQUEST_TIMEOUT = max(1, int(os.getenv("X_REQUEST_TIMEOUT", 20)))

# Per-user bot configuration: defaults + validation bounds.
DEFAULT_CONFIG = {
    "proxy": "",
    "proxies": "",
    "proxy_mode": "static",
    "proxy_session_format": "auto",
    "proxy_session_epoch": 0,
    "threads": 5,
    "limit": 1,
    "select_users": 1,
    "follow_mentioned": 0,
    "mentions_per_target": 1,
    "random_mention_position": 1,
    "delay_min": 1,
    "delay_max": 3,
    "account_delay_min": 10,
    "account_delay_max": 25,
    "pfp_image": "pfp.jpg",
    "display_name": "",
    "bio": "",
}

# Roles, most → least privileged.
ROLES = ("admin", "moderator", "user")
