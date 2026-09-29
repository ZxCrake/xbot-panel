import os

from flask import Blueprint, Response

bp = Blueprint("pages", __name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


def _serve(name: str) -> Response:
    with open(os.path.join(TEMPLATES_DIR, name), "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


@bp.route("/")
def index():
    return _serve("index.html")


@bp.route("/login")
def login():
    return _serve("login.html")


@bp.route("/admin/login")
def admin_login():
    return _serve("admin_login.html")


@bp.route("/admin")
def admin():
    return _serve("admin.html")
