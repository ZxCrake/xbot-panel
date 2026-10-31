"""Automatic X GraphQL query-ID refresh.

X rotates the query IDs embedded in its web bundle every few weeks. Instead of
editing `constants.py` by hand, this module fetches the daily-maintained
snapshot from fa0311/TwitterInternalAPIDocument, caches the operations the app
uses in ``DATA_ROOT/query_ids.json``, and falls back to the constants when the
network or cache is unavailable.

Refresh policy:
- A background daemon thread (started by ``create_app``) checks once an hour
  and fetches when the cache is older than 24 h.
- ``manage.py refresh-query-ids`` forces an immediate refresh.
- ``get()`` never performs network I/O: it returns the cached ID when present,
  otherwise the value from ``constants.py``. Requests therefore never block or
  fail because the tracker is unreachable.

Set ``XBOT_QUERY_IDS_AUTOREFRESH=0`` to disable the background thread (tests
do this).
"""
import json
import os
import re
import threading
import time
import urllib.request

from .. import settings
from . import constants

SOURCE_URL = (
    "https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/"
    "refs/heads/develop/docs/json/API.json"
)
CACHE_PATH = os.path.join(settings.DATA_ROOT, "query_ids.json")
TTL_SECONDS = 24 * 60 * 60
CHECK_INTERVAL = 60 * 60
FETCH_TIMEOUT = 15
RETRY_COOLDOWN = 60

# X operation name -> fallback attribute in constants.py
OPERATIONS = {
    "UpdateProfileEmail": "UPDATE_PROFILE_EMAIL_QUERYID",
    "UserByScreenName": "USER_BY_SCREEN_NAME_QUERYID",
    "ArticleEntityDraftCreate": "ARTICLE_DRAFT_CREATE_QUERYID",
    "ArticleEntityUpdateTitle": "ARTICLE_UPDATE_TITLE_QUERYID",
    "ArticleEntityUpdateContent": "ARTICLE_UPDATE_CONTENT_QUERYID",
    "ArticleEntityUpdateCoverMedia": "ARTICLE_UPDATE_COVER_QUERYID",
    "ArticleEntityPublish": "CREATE_ARTICLE_QUERYID",
    "Favoriters": "FAVORITERS_QUERYID",
    "Retweeters": "RETWEETERS_QUERYID",
    "TweetDetail": "TWEET_DETAIL_QUERYID",
    "SearchTimeline": "SEARCH_TIMELINE_QUERYID",
    "CreateTweet": "CREATE_TWEET_QUERYID",
    "CreateRetweet": "CREATE_RETWEET_QUERYID",
    "FavoriteTweet": "FAVORITE_TWEET_QUERYID",
    "CreateBookmark": "CREATE_BOOKMARK_QUERYID",
    "TweetResultByRestId": "TWEET_RESULT_BY_REST_ID_QUERYID",
}

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,64}$")

_lock = threading.Lock()
_ids: dict = {}
_loaded = False
_cache_fetched_at = 0.0
_last_attempt = 0.0
_thread_started = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _valid_id(value) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value))


def _fallback(operation: str) -> str:
    attr = OPERATIONS.get(operation)
    value = getattr(constants, attr, "") if attr else ""
    return value if _valid_id(value) else ""


def _auto_refresh_enabled() -> bool:
    return os.getenv("XBOT_QUERY_IDS_AUTOREFRESH", "1").strip().lower() not in (
        "0", "false", "off", "no")


def _load_cache() -> None:
    """Load the on-disk cache once (no network)."""
    global _loaded, _cache_fetched_at
    with _lock:
        if _loaded:
            return
        _loaded = True
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return
    if not isinstance(data, dict):
        return
    fetched_at = data.get("fetched_at")
    try:
        fetched_at = float(fetched_at or 0)
    except (TypeError, ValueError):
        fetched_at = 0.0
    raw_ids = data.get("ids")
    if not isinstance(raw_ids, dict):
        return
    clean = {op: qid for op, qid in raw_ids.items()
             if op in OPERATIONS and _valid_id(qid)}
    with _lock:
        _ids.update(clean)
        _cache_fetched_at = max(_cache_fetched_at, fetched_at)


def _write_cache(fetched: dict) -> None:
    tmp = CACHE_PATH + ".tmp"
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": time.time(), "source": SOURCE_URL,
                       "ids": fetched}, f, indent=2)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _fetch() -> dict:
    """Download and extract our operations from the tracker JSON."""
    req = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "xbot-query-id-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    graphql = doc.get("graphql") if isinstance(doc, dict) else None
    if not isinstance(graphql, dict):
        return {}
    out = {}
    for operation in OPERATIONS:
        entry = graphql.get(operation)
        query_id = entry.get("queryId") if isinstance(entry, dict) else None
        if _valid_id(query_id):
            out[operation] = query_id
    return out


# ── Public API ───────────────────────────────────────────────────────────────

def get(operation: str) -> str:
    """Return the current query ID for an X operation ('' when unknown).

    Reads the cache/constants only; never touches the network.
    """
    _load_cache()
    with _lock:
        query_id = _ids.get(operation, "")
    return query_id or _fallback(operation)


def cache_info() -> dict:
    """Snapshot for diagnostics / the management command."""
    _load_cache()
    with _lock:
        age = int(time.time() - _cache_fetched_at) if _cache_fetched_at else None
        return {
            "source": SOURCE_URL,
            "cache_path": CACHE_PATH,
            "fetched_at": _cache_fetched_at or None,
            "age_seconds": age,
            "ttl_seconds": TTL_SECONDS,
            "ids": dict(_ids),
            "fallbacks": {op: _fallback(op) for op in OPERATIONS},
        }


def refresh(force: bool = False, fetch=None) -> bool:
    """Fetch the tracker and update the cache. Returns True on success.

    Skips the network when the cache is still fresh (unless ``force``) or when
    a recent attempt failed. ``fetch`` is injectable for tests.
    """
    global _last_attempt, _cache_fetched_at
    _load_cache()
    now = time.time()
    with _lock:
        fresh = _cache_fetched_at and (now - _cache_fetched_at < TTL_SECONDS)
        if fresh and not force:
            return False
        if not force and (now - _last_attempt < RETRY_COOLDOWN):
            return False
        _last_attempt = now
    try:
        fetched = (fetch or _fetch)()
    except Exception:
        return False
    if not isinstance(fetched, dict):
        return False
    clean = {op: qid for op, qid in fetched.items()
             if op in OPERATIONS and _valid_id(qid)}
    if not clean:
        return False
    with _lock:
        _ids.update(clean)
        _cache_fetched_at = time.time()
    _write_cache(clean)
    return True


def _refresh_loop() -> None:
    while True:
        try:
            refresh()
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)


def start_background_refresh() -> None:
    """Start the daemon refresher (idempotent, disabled by env var)."""
    global _thread_started
    if not _auto_refresh_enabled():
        return
    with _lock:
        if _thread_started:
            return
        _thread_started = True
    threading.Thread(target=_refresh_loop, daemon=True,
                     name="query-id-refresh").start()


def _reset_state() -> None:
    """Test helper: clear in-memory state (the cache file is untouched)."""
    global _loaded, _cache_fetched_at, _last_attempt, _thread_started
    with _lock:
        _ids.clear()
        _loaded = False
        _cache_fetched_at = 0.0
        _last_attempt = 0.0
        _thread_started = False
