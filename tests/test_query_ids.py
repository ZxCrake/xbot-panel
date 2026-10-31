"""Automatic query-ID refresh: cache, TTL, fallback and validation."""
import json
import time

from xbot.x import constants, query_ids


def _reset(monkeypatch, tmp_path):
    monkeypatch.setattr(query_ids, "CACHE_PATH", str(tmp_path / "query_ids.json"))
    query_ids._reset_state()


def test_fallback_to_constants_when_no_cache(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    assert query_ids.get("Favoriters") == constants.FAVORITERS_QUERYID
    assert query_ids.get("CreateTweet") == constants.CREATE_TWEET_QUERYID
    assert query_ids.get("UserByScreenName") == constants.USER_BY_SCREEN_NAME_QUERYID


def test_refresh_writes_cache_and_get_uses_it(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    fetched = {"Favoriters": "NEWFAVORITESID12345",
               "UserByScreenName": "NEWUSERQUERYID1234"}
    assert query_ids.refresh(force=True, fetch=lambda: fetched) is True
    assert query_ids.get("Favoriters") == "NEWFAVORITESID12345"
    assert query_ids.get("UserByScreenName") == "NEWUSERQUERYID1234"
    cached = json.load(open(query_ids.CACHE_PATH, encoding="utf-8"))
    assert cached["ids"]["Favoriters"] == "NEWFAVORITESID12345"


def test_cache_survives_reload(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    query_ids.refresh(force=True, fetch=lambda: {"Favoriters": "CACHEDFAVID123456"})
    query_ids._reset_state()  # simulate a new process; cache file remains
    assert query_ids.get("Favoriters") == "CACHEDFAVID123456"


def test_fresh_cache_skips_network(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    query_ids.refresh(force=True, fetch=lambda: {"Favoriters": "FRESHID123456789"})
    calls = []

    def fetch():
        calls.append(1)
        return {}

    assert query_ids.refresh(fetch=fetch) is False
    assert calls == []


def test_stale_cache_refreshes(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(query_ids, "_cache_fetched_at",
                        time.time() - query_ids.TTL_SECONDS - 1)
    assert query_ids.refresh(fetch=lambda: {"Favoriters": "STALEID123456789"}) is True
    assert query_ids.get("Favoriters") == "STALEID123456789"


def test_invalid_ids_are_ignored(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    fetched = {"Favoriters": "bad id!", "Retweeters": "OKRETWEETID1234567"}
    assert query_ids.refresh(force=True, fetch=lambda: fetched) is True
    assert query_ids.get("Favoriters") == constants.FAVORITERS_QUERYID
    assert query_ids.get("Retweeters") == "OKRETWEETID1234567"


def test_failed_fetch_keeps_fallback(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)

    def boom():
        raise OSError("network down")

    assert query_ids.refresh(force=True, fetch=boom) is False
    assert query_ids.get("Favoriters") == constants.FAVORITERS_QUERYID


def test_unknown_operation_returns_empty(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    assert query_ids.get("DoesNotExist") == ""


def test_auto_refresh_disabled_by_env(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setenv("XBOT_QUERY_IDS_AUTOREFRESH", "0")
    query_ids.start_background_refresh()
    assert query_ids._thread_started is False
