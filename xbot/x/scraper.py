"""Scrape a tweet's engagement (likes / retweets / replies / quotes).

Uses the same XSession pipeline as the bot. Each function paginates via
cursors up to `max_results`. Parsing is done with a recursive walker so it's
resilient to X's frequently-changing response layout.

queryIds are version-specific (X rotates them). They live in the authenticated
web build: main.js inline ops, plus webpack chunks for the others (Favoriters/
Retweeters currently in bundle.TweetEditHistory). Refresh by scanning the
authenticated x.com/home build (see xbot/x/constants.py), not manual DevTools.
"""
import json
import time

from .session import XSession
from . import constants

GRAPHQL = "https://x.com/i/api/graphql/{qid}/{op}"


# ── Recursive extractors ─────────────────────────────────────────────────────

def _iter_dicts(obj):
    """Yield every dict nested anywhere in a JSON structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_dicts(v)


def _extract_users(data) -> list:
    """Find every User result and return {username, name}. Deduplicated."""
    seen, out = set(), []
    for d in _iter_dicts(data):
        if d.get("__typename") == "User":
            legacy = d.get("legacy") or d.get("core") or {}
            handle = legacy.get("screen_name") or d.get("screen_name")
            if handle and handle not in seen:
                seen.add(handle)
                out.append({"username": handle, "name": legacy.get("name", "")})
    return out


def _extract_tweet_authors(data, exclude_tweet_id: str) -> list:
    """Authors of tweets in the payload (for replies/quotes), minus the root."""
    seen, out = set(), []
    for d in _iter_dicts(data):
        if d.get("__typename") == "Tweet":
            rest_id = d.get("rest_id")
            if rest_id == exclude_tweet_id:
                continue
            user = None
            core = d.get("core", {})
            ur = (core.get("user_results") or {}).get("result")
            if ur:
                legacy = ur.get("legacy") or ur.get("core") or {}
                handle = legacy.get("screen_name")
                if handle and handle not in seen:
                    seen.add(handle)
                    out.append({"username": handle, "name": legacy.get("name", "")})
    return out


def _bottom_cursor(data):
    """Return the 'Bottom' pagination cursor value, or None."""
    for d in _iter_dicts(data):
        if d.get("cursorType") == "Bottom" and d.get("value"):
            return d["value"]
        # some layouts: entryId startswith 'cursor-bottom'
        if str(d.get("entryId", "")).startswith("cursor-bottom") and d.get("content", {}).get("value"):
            return d["content"]["value"]
    return None


# ── Generic paginated GraphQL walk ───────────────────────────────────────────

def _paginate(session: XSession, qid: str, op: str, base_vars: dict,
              extract, max_results: int, referer: str, delay: float = 1.2) -> dict:
    if not qid:
        return {"error": f"{op} queryId manquant (voir constants.py)", "items": []}
    url = GRAPHQL.format(qid=qid, op=op)
    items, seen, cursor, pages = [], set(), None, 0
    while len(items) < max_results and pages < 60:
        variables = dict(base_vars)
        if cursor:
            variables["cursor"] = cursor
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(constants.SCRAPE_FEATURES),
        }
        try:
            r = session.get(url, params, referer)
        except Exception as e:
            return {"error": f"request failed: {e}", "items": items}
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code} (queryId/features ?)", "items": items}
        try:
            data = r.json()
        except Exception:
            return {"error": "bad JSON", "items": items}
        if data.get("errors") and not data.get("data"):
            return {"error": str(data["errors"])[:200], "items": items}

        batch = extract(data)
        new = [u for u in batch if u["username"] not in seen]
        for u in new:
            seen.add(u["username"])
        items.extend(new)

        cursor = _bottom_cursor(data)
        pages += 1
        if not cursor or not new:
            break
        time.sleep(delay)

    return {"items": items[:max_results], "count": len(items[:max_results])}


# ── Public functions ─────────────────────────────────────────────────────────

def favoriters(session, tweet_id, max_results=500):
    return _paginate(
        session, constants.FAVORITERS_QUERYID, "Favoriters",
        {"tweetId": tweet_id, "count": 100, "includePromotedContent": False},
        _extract_users, max_results, f"https://x.com/i/status/{tweet_id}/likes",
    )


def retweeters(session, tweet_id, max_results=500):
    return _paginate(
        session, constants.RETWEETERS_QUERYID, "Retweeters",
        {"tweetId": tweet_id, "count": 100, "includePromotedContent": False},
        _extract_users, max_results, f"https://x.com/i/status/{tweet_id}/retweets",
    )


def replies(session, tweet_id, max_results=500):
    return _paginate(
        session, constants.TWEET_DETAIL_QUERYID, "TweetDetail",
        {"focalTweetId": tweet_id, "referrer": "tweet", "with_rux_injections": False,
         "includePromotedContent": False, "withCommunity": True,
         "withQuickPromoteEligibilityTweetFields": True, "withBirdwatchNotes": True,
         "withVoice": True, "withV2Timeline": True},
        lambda d: _extract_tweet_authors(d, tweet_id), max_results,
        f"https://x.com/i/status/{tweet_id}",
    )


def quotes(session, tweet_id, max_results=500):
    q = f"https://x.com/i/status/{tweet_id}"
    return _paginate(
        session, constants.SEARCH_TIMELINE_QUERYID, "SearchTimeline",
        {"rawQuery": f"quoted_tweet_id:{tweet_id}", "count": 40, "querySource": "typed_query",
         "product": "Top"},
        lambda d: _extract_tweet_authors(d, tweet_id), max_results,
        "https://x.com/search",
    )


SCRAPERS = {
    "likes": favoriters,
    "retweets": retweeters,
    "replies": replies,
    "quotes": quotes,
}
