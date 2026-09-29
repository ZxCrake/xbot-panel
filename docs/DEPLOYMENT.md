# Deployment & Operations Guide

Production deployment of the X Automation panel on a Linux server.

---

## 1. Architecture

```
            ┌─────────────┐   HTTPS    ┌──────────────┐
  Browser ──┤    nginx    ├───────────►│  gunicorn    │   (run:app, 1 worker / N threads)
            │ TLS + proxy │   :443     │  Flask app   │
            └─────────────┘            └───┬──────┬───┘
                                           │      │
                                   ┌───────▼─┐  ┌─▼────────┐
                                   │Postgres │  │  Redis   │  (rate-limit store)
                                   └─────────┘  └──────────┘
```

- **Auth:** stateless signed Bearer tokens (Argon2id password hashing, per-user
  `token_version` for revocation). No cookies → inherently CSRF-resistant.
- **DB:** PostgreSQL (recommended) or SQLite. Schema managed by **Alembic**.
- **Single web worker:** bot job state is in-process memory, so gunicorn runs
  **1 worker with many threads** (see `gunicorn.conf.py`). Do not scale workers.

---

## 2. Configuration (`.env`)

Copy `.env.example` → `.env` and set every value. Critical ones:

| Var | Notes |
|-----|-------|
| `SECRET_KEY` | **Required.** `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `postgresql+psycopg2://xbot:PASS@db:5432/xbot` |
| `FRONTEND_ORIGIN` | Exact panel URL, or empty for same-origin |
| `RATELIMIT_STORAGE_URI` | `redis://redis:6379/0` in production |
| `BEHIND_PROXY` | `true` when served via nginx (enables HSTS + correct client IP) |
| `POSTGRES_PASSWORD` | strong DB password (used by docker-compose) |

`.env` is gitignored and never baked into the image.

---

## 3. Deploy with Docker (recommended)

```bash
git clone <repo> /opt/xbot && cd /opt/xbot
cp .env.example .env && nano .env          # fill SECRET_KEY, passwords, domain

# TLS certificate (first issue): point DNS at the server, then:
#   docker compose run --rm certbot ...   (or use your own certs in deploy/certbot)
# Edit deploy/nginx/xbot.conf — replace panel.example.com with your domain.

docker compose up -d --build               # migrations run automatically on start
docker compose exec app python manage.py add <admin> <password> admin
```

Visit `https://your-domain/` (users) or `https://your-domain/admin/login` (admins).

Updating:
```bash
git pull && docker compose up -d --build   # alembic upgrade head runs on boot
```

---

## 4. Deploy on bare metal (systemd)

```bash
sudo useradd --system --create-home --home-dir /opt/xbot xbot
sudo -u xbot git clone <repo> /opt/xbot && cd /opt/xbot
sudo -u xbot python3.12 -m venv .venv
sudo -u xbot .venv/bin/pip install -r requirements.txt
sudo -u xbot cp .env.example .env   # edit it
sudo -u xbot .venv/bin/alembic upgrade head
sudo -u xbot .venv/bin/python manage.py add <admin> <password> admin

sudo cp deploy/xbot.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now xbot
# Put nginx (deploy/nginx/xbot.conf) in front with certbot for TLS.
```

---

## 4b. Deploy on Fly.io

Fly works well, with one rule: **run exactly one machine.** The bot's job state
is in-process memory, so multiple machines would each see different running jobs.
`fly.toml` already pins `min/max_machines_running = 1` and disables auto-stop.

```bash
fly launch --no-deploy            # or `fly apps create xbot-panel`; keep the provided fly.toml
fly volumes create xbot_data --size 1 --region cdg     # persistent DB + user files
fly secrets set SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
# Optional: managed Postgres instead of the volume's SQLite
#   fly postgres create && fly postgres attach <pg-app>   # sets DATABASE_URL secret
fly deploy                        # builds the Dockerfile; entrypoint runs migrations

# Create the first admin (one-off, inside the running machine):
fly ssh console -C "python manage.py add admin 'StrongPass123' admin"
```

Notes:
- TLS is handled by Fly's proxy (`force_https = true`); the app keeps `BEHIND_PROXY=true`.
- A **volume is required even with Postgres** — each user's `accounts.txt`,
  `tweets.txt`, etc. and logs live on disk under `/app/data`.
- Never `fly scale count 2+`. To handle more web users, raise `threads` in `gunicorn.conf.py`.
- Logs: `fly logs`. Shell: `fly ssh console`.

## 5. Database migrations

```bash
alembic upgrade head          # apply latest (run on every deploy)
alembic revision -m "msg"     # create a new migration after model changes
alembic downgrade -1          # roll back one
```

The Docker entrypoint runs `alembic upgrade head` automatically before starting.

---

## 6. Backups

`scripts/backup_db.sh` dumps Postgres (or SQLite) gzip'd and prunes old files.

```bash
# nightly cron (bare metal)
0 3 * * *  /opt/xbot/scripts/backup_db.sh >> /var/log/xbot-backup.log 2>&1

# docker
0 3 * * *  docker compose -f /opt/xbot/docker-compose.yml exec -T db \
             pg_dump -U xbot xbot | gzip > /opt/xbot/backups/xbot-$(date +\%F).sql.gz
```

Keep backups off-host (S3, rsync) as well. Test a restore periodically.

---

## 7. Security checklist

- [x] Passwords hashed with **Argon2id**; never stored or logged in clear.
- [x] **TLS** enforced at nginx; HSTS sent by the app behind the proxy.
- [x] **Brute-force**: account lockout after `LOGIN_MAX_ATTEMPTS`; IP rate-limit on `/api/login`.
- [x] **Rate limiting** globally (Flask-Limiter, Redis-backed).
- [x] **Security headers**: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
- [x] **SQL injection**: SQLAlchemy ORM (parameterized) only.
- [x] **CSRF**: Bearer-token auth (no ambient cookies).
- [x] **Input validation** server-side (config bounds, file whitelist + size caps, username/password rules).
- [x] **Path traversal**: editable files are whitelisted; PFP filename forced to a safe basename.
- [x] **RBAC**: admin / moderator / user; moderators read-only in admin.
- [x] **Audit log** (DB + file) for logins and sensitive actions.
- [ ] Run `pip-audit -r requirements.txt` in CI and before releases.
- [ ] Rotate `SECRET_KEY` only when you intend to invalidate all sessions.
- [ ] Restrict DB and Redis to the internal network (compose does this by default).

## 8. Maintenance

- **Logs:** `docker compose logs -f app` or `journalctl -u xbot -f`; app logs also in `data/logs/xbot.log` (rotated).
- **Revoke a user's sessions:** change their password, or `python manage.py role <user> <role>` (both bump `token_version`).
- **Dependency audit:** `pip install pip-audit && pip-audit -r requirements.txt`.
- **Tests:** `pip install -r requirements-dev.txt && pytest -q`.
- **Scaling note:** the bot runner is single-process by design. To serve more
  concurrent web users, raise `threads` in `gunicorn.conf.py`; do **not** raise `workers`.
