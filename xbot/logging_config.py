"""Logging setup: rotating file handler + console, structured-ish format."""
import os
import logging
from logging.handlers import RotatingFileHandler

from . import settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s | %(message)s"


def configure_logging():
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    root = logging.getLogger()
    if getattr(root, "_xbot_configured", False):
        return
    root.setLevel(level)

    fmt = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        fh = RotatingFileHandler(
            os.path.join(settings.LOG_DIR, "xbot.log"),
            maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass  # file logging optional (e.g. read-only FS)

    # Quiet noisy libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    root._xbot_configured = True  # type: ignore
