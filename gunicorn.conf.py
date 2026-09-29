"""Gunicorn production config.

IMPORTANT: workers must be 1. Bot job state (BotRunner) lives in process
memory, so multiple workers would each see a different view of running jobs.
Concurrency is provided by threads instead.
"""
import multiprocessing  # noqa: F401 (kept for reference; do not scale workers)

bind = "0.0.0.0:5000"
workers = 1
threads = 16
worker_class = "gthread"
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = "-"      # stdout (captured by Docker / systemd / journald)
errorlog = "-"
loglevel = "info"
forwarded_allow_ips = "*"   # behind nginx; ProxyFix handles the rest
