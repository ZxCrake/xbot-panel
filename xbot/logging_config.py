"""Logging setup: rotating file handler + console, structured-ish format."""
import os
import logging
from logging.handlers import RotatingFileHandler

from . import settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s | %(message)s"


def configure_logging():
    """Attach the app handlers to the root logger (idempotent).

    Handlers are tagged so a second call (or a library that calls
    ``logging.config.fileConfig``) cannot leave us without console/file output.
    """
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(_FORMAT)

    if not any(getattr(h, "_xbot_handler", "") == "console" for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console._xbot_handler = "console"  # type: ignore[attr-defined]
        root.addHandler(console)

    if not any(getattr(h, "_xbot_handler", "") == "file" for h in root.handlers):
        try:
            fh = RotatingFileHandler(
                os.path.join(settings.LOG_DIR, "xbot.log"),
                maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
            )
            fh.setFormatter(fmt)
            fh._xbot_handler = "file"  # type: ignore[attr-defined]
            root.addHandler(fh)
        except OSError:
            pass  # file logging optional (e.g. read-only FS)

    # Request lines are useful in development; production uses gunicorn's
    # access log instead.
    logging.getLogger("werkzeug").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING)
    # Some libraries (notably Alembic's fileConfig) disable loggers that
    # already existed; make sure the app logger stays active.
    logging.getLogger("xbot").disabled = False
    root._xbot_configured = True  # type: ignore
