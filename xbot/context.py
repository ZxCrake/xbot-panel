import os
import json
from threading import Lock

from flask import g, abort

from . import auth
from .farm import FarmRunner
from .runner import BotRunner
from .settings import DEFAULT_CONFIG
from . import settings
from .files import workspace_path, safe_file

# One BotRunner per user (in-memory job state). NOTE: requires a single web
# worker process — see deployment docs (gunicorn --workers 1 --threads N).
runners: dict[str, BotRunner] = {}
runners_lock = Lock()

# One FarmRunner per user — la ferme (réchauffement autonome des comptes).
# État persistant dans farm_state.json : reprise automatique après restart.
farms: dict[str, FarmRunner] = {}


def workspace_is_active(key: str) -> bool:
    # A fresh connection also observes deletions made through manage.py.
    from sqlalchemy import select
    from .db import get_engine, User
    with get_engine().connect() as connection:
        return bool(connection.execute(
            select(User.is_active).where(User.workspace_key == key)
        ).scalar())


def current_user() -> str:
    return getattr(g, "user", "")


def current_role() -> str:
    return getattr(g, "role", "")


def current_dir() -> str:
    d = workspace_path(settings.USER_DATA_ROOT, g.workspace_key)
    os.makedirs(d, exist_ok=True)
    return d


def get_runner() -> BotRunner:
    user = current_user()
    with runners_lock:
        # Refresh inside the registry lock: a request authenticated before
        # deletion must not recreate a runner after it has been retired.
        from .db import session, User
        u = session().query(User).populate_existing().filter_by(username=user).first()
        if not u or not u.is_active or u.workspace_key != g.workspace_key:
            abort(401)
        key = u.workspace_key
        if key not in runners:
            runners[key] = BotRunner(authorized=lambda: workspace_is_active(key))
        return runners[key]


def get_farm() -> FarmRunner:
    user = current_user()
    with runners_lock:
        from .db import session, User
        u = session().query(User).populate_existing().filter_by(username=user).first()
        if not u or not u.is_active or u.workspace_key != g.workspace_key:
            abort(401)
        key = u.workspace_key
        if key not in farms:
            f = FarmRunner(base_dir=workspace_path(settings.USER_DATA_ROOT, key),
                           authorized=lambda: workspace_is_active(key))
            f.maybe_resume()
            farms[key] = f
        return farms[key]


def farm_busy() -> bool:
    """La ferme tourne-t-elle pour l'utilisateur courant ?"""
    try:
        return get_farm().running
    except Exception:
        return False


def read_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    path = safe_file(current_dir(), "config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def write_config(updates: dict):
    """Merge validated updates into the stored config (defaults preserved)."""
    cfg = read_config()
    cfg.update(updates or {})
    path = safe_file(current_dir(), "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
