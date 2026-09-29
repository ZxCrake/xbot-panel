import logging

from flask import Flask, jsonify, request, abort
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from . import settings
from .db import init_engine, upgrade_schema, session
from .logging_config import configure_logging
from .security import limiter, apply_security_headers, apply_cors

log = logging.getLogger("xbot")


def create_app() -> Flask:
    configure_logging()
    init_engine()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        MAX_CONTENT_LENGTH=settings.MAX_PFP_BYTES + 1024 * 1024,  # cap request body
        JSON_SORT_KEYS=False,
    )

    # Trust the reverse proxy for client IP / scheme (nginx).
    if settings.BEHIND_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    limiter.init_app(app)

    @app.before_request
    def _json_object():
        if request.is_json and not isinstance(request.get_json(silent=True), dict):
            abort(400, description="JSON body must be an object")

    # ── lifecycle ──
    @app.teardown_appcontext
    def _remove_session(exc=None):
        session().remove()

    # ── headers ──
    @app.after_request
    def _headers(resp):
        return apply_cors(apply_security_headers(resp))

    @app.route("/<path:_any>", methods=["OPTIONS"])
    def _cors_preflight(_any=""):
        return ("", 204)

    # ── health ──
    @app.route("/health")
    @limiter.exempt
    def health():
        return jsonify({"service": "x-automation-api", "ok": True})

    # ── error handlers (always JSON for the API) ──
    @app.errorhandler(HTTPException)
    def _http_err(e):
        return jsonify({"error": e.name.lower().replace(" ", "_"), "message": e.description}), e.code

    @app.errorhandler(Exception)
    def _unhandled(e):
        log.exception("unhandled error on %s %s", request.method, request.path)
        try:
            session().rollback()
        except Exception:
            pass
        return jsonify({"error": "internal_error"}), 500

    # ── routes ──
    from .routes import register
    register(app)

    # SQLite/dev convenience: ensure tables exist. In production, use Alembic.
    if settings.DATABASE_URL.startswith("sqlite"):
        upgrade_schema()

    log.info("app created (env=%s, db=%s)", settings.ENV, settings.DATABASE_URL.split("://")[0])
    return app
