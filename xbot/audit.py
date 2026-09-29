"""Audit + application logging.

`log_action` writes a structured row to the audit_logs table AND emits a log
line. Use it for security-relevant events (logins, user CRUD, job control).
"""
import logging

from flask import request, has_request_context

from .db import session, AuditLog

logger = logging.getLogger("xbot.audit")


def client_ip() -> str | None:
    if not has_request_context():
        return None
    # ProxyFix populates remote_addr from X-Forwarded-For when behind nginx.
    return request.remote_addr or None


def log_action(action: str, username: str | None = None, detail: str | None = None):
    ip = client_ip()
    logger.info("action=%s user=%s ip=%s detail=%s", action, username, ip, detail)
    try:
        s = session()
        s.add(AuditLog(action=action, username=username, detail=detail, ip=ip))
        s.commit()
    except Exception:  # never let auditing break the request
        logger.exception("failed to write audit row")
        try:
            session().rollback()
        except Exception:
            pass
