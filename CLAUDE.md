# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Multi-user X (Twitter) automation panel: a Flask JSON API + server-rendered HTML/JS UI, plus a standalone console bot (`cli/run_cli.py`). Each user gets an isolated workspace under `data/users/<workspace_key>/`. Two execution engines coexist: manual jobs (`BotRunner`, 13 action modes) and an autonomous warm-up farm (`FarmRunner`). The X engine talks to X's private web GraphQL API using `auth_token` cookies — not OAuth.

## Commands (Windows development)

```bash
# This machine's working venv is venv/ (uv-managed CPython 3.12).
# .venv/ is a Linux venv created under WSL and CANNOT run on Windows.
venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Run the dev server (reads .env; XBOT_ENV=development → SQLite at data/xbot.db)
venv\Scripts\python.exe run.py            # http://localhost:5000

# Tests (pass tests/ explicitly; see note below)
venv\Scripts\python.exe -m pytest -q tests
venv\Scripts\python.exe -m pytest -q tests/test_proxies.py
venv\Scripts\python.exe -m pytest -q tests/test_proxies.py::TestResolveForAccount::test_rotating_single_line_reused_across_slots
# Bare `pytest -q` also collects tools/test_account.py (a CLI, not a test) and
# fails with "fixture 'user' not found"; add `testpaths = tests` to a pytest.ini
# (or keep passing tests/ explicitly).

# Read-only account diagnostics (auth, profile, proxy, query IDs)
venv\Scripts\python.exe tools/test_account.py --workspace data/users/<workspace_key> --index 0
venv\Scripts\python.exe tools/test_account.py --workspace data/users/<workspace_key> --all

# Admin / users / query IDs
venv\Scripts\python.exe manage.py init
venv\Scripts\python.exe manage.py add <username> <password> admin
venv\Scripts\python.exe manage.py list
venv\Scripts\python.exe manage.py refresh-query-ids
```

**SQLite dev warning:** stop the server before running `manage.py` write commands (`add/passwd/del/role/upgrade/refresh-query-ids`). Concurrent writers leave a stale `data/xbot.db-journal`; the running server then returns `500 {"error":"internal_error"}` on every write path, including `/api/login`. Recover by stopping the server, opening the DB once with `sqlite3` (it rolls back/removes the journal), then restarting.

Production / Linux:

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
gunicorn -c gunicorn.conf.py run:app      # 1 worker / N threads by design
docker compose up -d --build              # app + Postgres + Redis + nginx; entrypoint runs migrations
```

## Architecture

- **App factory** `xbot.create_app()` (`xbot/__init__.py`): logging, SQLAlchemy engine, rate limiter, security headers/CORS, JSON error handlers, blueprint registration, SQLite schema upgrade, and the query-ID background refresher.
- **Entrypoints**: `run.py` (exposes `app` for gunicorn), `manage.py` (admin CLI), `cli/run_cli.py` (standalone bot reading `./workspace`), `tools/test_account.py` (read-only account diagnostics; a CLI, not a pytest test).
- **Blueprints** (`xbot/routes/`):
  - `auth`: `/api/login`, `/api/me`, `/api/actions`.
  - `user`: per-user config, file editing/upload, `/api/run|stop|status`, `/api/scrape`, `/api/articles`, farm control, proxy session rotation.
  - `admin`: user CRUD and read-only detail (admin role).
  - `pages`: `/`, `/login`, `/admin/login`, `/admin`; `/health` is defined in `create_app`.
- **Auth** (`xbot/auth.py`): Argon2id hashes; stateless `itsdangerous` Bearer tokens (default 7 days) carrying `token_version` for global revocation; roles admin > moderator > user; per-account brute-force lockout; audit log to DB + file. Token auth (not cookies) means no CSRF surface; CORS only when `FRONTEND_ORIGIN` is set.
- **DB** (`xbot/db.py`): SQLAlchemy models `User` and `AuditLog`; Alembic migrations in `migrations/`. SQLite in dev, Postgres in prod (`DATABASE_URL`). Each user's `workspace_key` (`u-<uuid>`) maps to their data directory; all file access goes through `xbot/files.py` (`safe_file` blocks traversal/symlinks).
- **Manual jobs** (`xbot/runner.py`): one `BotRunner` per user in `context.runners` (in-process memory → **single WSGI worker mandatory**). Threads process accounts concurrently. `ACTION_NAMES`: 1 quote, 2 retweet, 3 like, 4 reply, 5 view, 6 bookmark, 7 cross-follow, 8 PFP, 9 name/bio, 10 premium check, 11 article, 12 follow target, 13 DM, 14 change email (from `emails.txt`, one `adresse:mot_de_passe` line per account). `TWEET_ID_ACTIONS=(2..6)`, `ONCE_ACTIONS=(7..14)`, `TARGET_ACTIONS=(1,12,13)`; target actions consume a shared thread-safe `TargetPool`. Results go to `JobStats` and `history.log`. Tweet creation inspects `__typename` to detect hidden/limited tweets (`TweetWithVisibilityResults`, tombstone).
- **Farm** (`xbot/farm.py`): one `FarmRunner` per user in `context.farms`, state persisted in `farm_state.json`. Generates daily per-account action plans, executes ≤1 action/account/tick, computes a 0–100 humanisation score (visibility 40, follower growth 20, activity days 20, profile 10, integrity 10), and resumes after a restart. Action kinds are `follow`, `like`, `retweet`, `bookmark`, `view`, `tweet`, fed by the `users` / `tweet_ids` / `tweets` content channels. Content banks and public tweet-ID fetching live in `xbot/farm_content.py`.
- **X engine** (`xbot/x/`):
  - `session.py` — `XSession` (curl_cffi, chrome124): loads x.com/home, fetches ct0, guest token and XPFF, then signs GraphQL requests with `x-client-transaction-id`.
  - `actions.py` — GraphQL mutations/REST 1.1 actions: quote/reply/like/retweet/bookmark/view/follow/PFP/name-bio/DM and the 5-step article publication.
  - `scraper.py` — read-only paginated `Favoriters`, `Retweeters`, `TweetDetail`, `SearchTimeline`, with recursive parsing resilient to layout changes.
  - `query_ids.py` — auto-refreshes GraphQL query IDs daily from the fa0311 tracker into `data/query_ids.json`; falls back to `constants.py`. `query_ids.get(op)` never touches the network. A daemon thread starts in `create_app`; `manage.py refresh-query-ids` forces a refresh.
  - `constants.py` — bearer token, UA/headers, feature dicts, and fallback query IDs. Do not hardcode query IDs elsewhere.
  - `articles.py` — converts the panel's contenteditable article HTML into X's Draft.js `content_state` (snake_case blocks/entity_map), including `@mention` / `#hashtag` / `$cashtag` spans.
  - `proxies.py` — `static` mode maps line i to account i; `rotating` mode reuses gateway lines round-robin with a unique sticky session per account (formats: `auto`, `generic`, `dataimpulse`). `coverage_error` refuses a static job when there are more accounts than proxy lines and no fallback.
  - `media.py` / `xpff.py` — media upload and XPFF header generation.
- **Frontend**: `xbot/templates/*.html` + `xbot/static/*.js|css`, served by Flask with no build step. The CSP forbids inline scripts; keep JS in `static/`.
- **Tests** (`tests/`): `conftest.py` sets a throwaway `DATA_ROOT`/DB before importing the app, disables query-ID auto-refresh, and blocks curl_cffi network calls. New network paths must be injectable/mockable.

## Domain gotchas

- Every GraphQL operation should resolve through `query_ids.get("<OperationName>")`; `constants.py` values are fallbacks only.
- Article publishing is a sequence: `ArticleEntityDraftCreate → ArticleEntityUpdateTitle → ArticleEntityUpdateContent → ArticleEntityUpdateCoverMedia (optional) → ArticleEntityPublish`. The content step uses the variable name `article_entity`; the others use `articleEntityId`. Articles require an X Premium subscription (all Premium tiers since Jan 2026); `check_premium` gates the action.
- Rotating proxies: a single backconnect line can serve all accounts; lines are reused round-robin and each account index gets its own sticky session. `proxy_session_format` is `auto` (DataImpulse detected by host), `generic` (`user-session-<id>`), or `dataimpulse` (`user;sessid.<id>`). `coverage_error` only refuses static mode when there are more accounts than lines and no fallback.
- `accounts.txt` canonical format is `username:auth_token`; the runner reads `split(":")[0]` and `split(":")[-1]`. `/api/import-accounts` keeps the chosen middle fields (e.g. `PASS`) in their order: `username:[extras…]:auth_token`. Action 14 uses field n°2 as the X account password; Gmail credentials live in `emails.txt` (`adresse:mot_de_passe`), created via `tools/gmail_create.mjs` (Puppeteer + 2captcha).
- Adding a config key touches four places: `settings.DEFAULT_CONFIG`, `security.validate_config` whitelists (`_INT_BOUNDS` / `_STR_FIELDS` / `_BOOL_FIELDS`), the `CFG` array in `static/index.js`, and the matching input in `templates/index.html`.
- `sandbox/account.txt` is untracked but not gitignored and contains credentials; do not commit it.
- Logging: `xbot/logging_config.py` attaches console + rotating-file handlers. Alembic's `fileConfig` is deliberately disabled (`config.config_file_name = None` in `db.upgrade_schema`) because it disables the `xbot` logger and removes the handlers.
- `docs/backend.md` contains historical details (e.g. it still says article publishing is unavailable); prefer the current code. README points to `docs/SECURITY_UPDATE.md` for the existing-install migration and `docs/DEPLOYMENT.md` for production.
- Windows: use `venv/`; the app/farm state is in memory, so never run multiple gunicorn workers.

## Environment gotchas (this Windows host)

- Host is Windows 11 **ARM64** (Snapdragon X Plus); `venv/` is an **x86_64** uv CPython running under emulation. This matters for native wheels (`curl_cffi`, `cffi`).
- `curl_cffi==0.7.4` has no `win_arm64` wheel. On concurrent authenticated jobs its bundled `libcurl` can call `abort()` and kill the whole Flask process (Windows Error Reporting `0x40000015` in `msvcrt.dll`; the dump stack shows `libcurl`). The server window then closes, and `try/except` cannot catch it. Candidate fixes: `curl_cffi==0.17.0` (win_amd64) or a native ARM64 Python + `win_arm64` wheel; validate in a temporary venv first. Crash dumps land in `%LOCALAPPDATA%\CrashDumps`.
