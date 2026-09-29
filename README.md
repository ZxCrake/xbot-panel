# X Automation

Multi-user X (Twitter) automation panel — Flask API + web UI, with a standalone CLI.

Existing installation: read [the security update and migration notes](docs/SECURITY_UPDATE.md)
before restarting. Existing sessions must sign in again.

## Quick start (development)

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env                               # set SECRET_KEY at minimum
export XBOT_ENV=development                        # uses local SQLite by default

python manage.py init                              # create tables
python manage.py add admin 'StrongPass123' admin   # first administrator
python run.py                                       # http://localhost:5000
```

- User panel: `http://localhost:5000/` → `/login`
- Admin console: `http://localhost:5000/admin/login`

Run the tests: `pytest -q`

## Production

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Docker Compose (app + Postgres +
Redis + nginx/TLS) or systemd, migrations, backups, and the security checklist.

## Project layout

```
run.py                  API entrypoint (gunicorn: run:app)
manage.py               Admin CLI: user management (add / passwd / role / del / list)
gunicorn.conf.py        Production WSGI config (1 worker / N threads — see docs)
alembic.ini, migrations/  Database schema migrations
requirements*.txt       Pinned dependencies (runtime / dev)

xbot/                   Backend package
├── __init__.py         create_app(): factory (DB, limiter, headers, errors, logging)
├── settings.py         Centralized env/.env configuration
├── db.py               SQLAlchemy engine + models (User, AuditLog)
├── auth.py             Argon2 hashing, signed tokens, roles, brute-force lockout
├── audit.py            Audit log (DB + file)
├── security.py         Rate limiter, security headers, input validation
├── logging_config.py   Rotating file + console logging
├── context.py          Per-user runtime helpers
├── runner.py           BotRunner: background jobs, stats, history
├── routes/             Blueprints: auth, user, admin, pages
└── x/                  X client engine (constants, session, actions, xpff)

cli/                    Standalone console bot (reads ./workspace)
tools/                  Independent utilities (scrapper, formatter, blue_gen)
deploy/                 nginx config, systemd unit, certbot dir
docker/                 Container entrypoint
scripts/                DB backup script
tests/                  pytest suite (auth, RBAC, endpoints, validation)
data/                   Runtime data (DB, per-user files, logs) — gitignored
```

## Roles

- **admin** — full access, user management.
- **moderator** — read-only access to the admin console (view users & activity).
- **user** — own workspace only.
