import os
import json
from collections import deque

from flask import Blueprint, request, jsonify

from .. import auth
from ..auth import admin_required, roles_required
from ..context import current_user, runners, runners_lock
from .. import settings
from ..files import safe_file

bp = Blueprint("admin", __name__)


def _count_lines(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


@bp.route("/api/admin/users", methods=["GET", "POST"])
@roles_required("moderator")  # moderator+ may view; creation gated below
def users():
    if request.method == "POST":
        # Viewing is moderator+, but creating a user requires admin.
        from flask import g
        if g.role != "admin":
            return jsonify({"error": "forbidden"}), 403
        data = request.get_json(silent=True) or {}
        role = data.get("role") or ("admin" if data.get("is_admin") else "user")
        try:
            auth.create_user(data.get("username", ""), data.get("password", ""), role=role)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"ok": True})

    out = []
    for u in auth.list_users():
        d = auth.user_dir(u.username)
        with runners_lock:
            runner = runners.get(u.workspace_key)
        running = bool(runner and runner.is_running())
        out.append({
            "username": u.username,
            "role": u.role,
            "is_admin": u.is_admin,
            "accounts": _count_lines(os.path.join(d, "accounts.txt")),
            "running": running,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        })
    return jsonify({"users": out})


@bp.route("/api/admin/users/<name>", methods=["DELETE"])
@admin_required
def delete_user(name):
    name = name.strip().lower()
    if name == current_user():
        return jsonify({"error": "you cannot delete your own account"}), 400
    if not auth.delete_user(name):
        return jsonify({"error": "user not found"}), 404
    return jsonify({"ok": True})


@bp.route("/api/admin/users/<name>/password", methods=["POST"])
@admin_required
def set_password(name):
    data = request.get_json(silent=True) or {}
    try:
        if not auth.set_password(name, data.get("password", "")):
            return jsonify({"error": "user not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@bp.route("/api/admin/users/<name>/detail")
@admin_required
def user_detail(name):
    name = name.strip().lower()
    user = auth.get_user(name)
    if not user:
        return jsonify({"error": "user not found"}), 404
    d = auth.user_dir(name)

    cfg = {}
    cfg_path = safe_file(d, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    files = {}
    for fname in settings.EDITABLE_FILES:
        p = safe_file(d, fname)
        content = ""
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        files[fname] = content

    history = []
    hist_path = safe_file(d, "history.log")
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            for line in deque(f, maxlen=500):
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    history.reverse()

    with runners_lock:
        runner = runners.get(user.workspace_key)
    live = runner.status() if runner else {}
    return jsonify({"config": cfg, "files": files, "history": history, "live": live})
