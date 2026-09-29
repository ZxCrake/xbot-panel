from flask import Blueprint, request, jsonify

from .. import auth
from ..auth import login_required
from ..context import current_user, current_role
from ..runner import ACTION_NAMES
from ..security import limiter

bp = Blueprint("auth", __name__)


@bp.route("/api/login", methods=["POST"])
@limiter.limit("10 per minute; 30 per hour")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username") or ""
    password = data.get("password") or ""
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "username and password must be strings"}), 400
    username = username.strip().lower()
    if len(username) > 32 or len(password) > 128:
        return jsonify({"error": "credentials too long"}), 400
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    user = auth.authenticate(username, password)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401
    return jsonify({
        "token": auth.generate_token(user),
        "username": user.username,
        "role": user.role,
        "is_admin": user.is_admin,
    })


@bp.route("/api/me")
@login_required
def me():
    return jsonify({
        "username": current_user(),
        "role": current_role(),
        "is_admin": current_role() == "admin",
    })


@bp.route("/api/actions")
@login_required
def actions():
    return jsonify({str(k): v for k, v in ACTION_NAMES.items()})
