"""Tests de la génération automatique du contenu de vie (farm_content)
et des nouveaux profils de cadence (slow / fast)."""

import random
import re

import pytest

from xbot import farm as farm_mod
from xbot import farm_content as fc


# ── Banques statiques ─────────────────────────────────────────────────────────

def test_sanity_check_banks():
    assert fc.sanity_check() == []


def test_users_bank_handles_valid():
    for u in fc.USERS_BANK:
        assert re.match(r"^[A-Za-z0-9_]{1,15}$", u), u


@pytest.mark.parametrize("bank", [fc.POSTS_BANK_FR, fc.POSTS_BANK_EN])
def test_posts_templates_mutate_safe(bank):
    for t in bank:
        for _ in range(3):  # chaque tirage doit rester dans les bornes
            out = farm_mod.mutate_text(t)
            assert len(out) <= 280
            assert "@" not in out
            assert "http" not in out.lower()
            assert "{" not in out and "}" not in out  # spintax consommé


# ── generate() ────────────────────────────────────────────────────────────────

def test_generate_users():
    lines = fc.generate("users")
    assert 0 < len(lines) <= 30
    assert len(set(lines)) == len(lines)
    assert set(lines) <= set(fc.USERS_BANK)


def test_generate_posts_fr_en():
    fr = fc.generate("posts", lang="fr")
    en = fc.generate("posts", lang="en")
    assert len(fr) == 20 and set(fr) <= set(fc.POSTS_BANK_FR)
    assert len(en) == 20 and set(en) <= set(fc.POSTS_BANK_EN)


def test_generate_tweet_ids_passthrough(monkeypatch):
    monkeypatch.setattr(fc, "fetch_recent_tweet_ids",
                        lambda handles, **kw: ["123", "456"])
    assert fc.generate("tweet_ids") == ["123", "456"]


def test_generate_tweet_ids_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(fc, "fetch_recent_tweet_ids", lambda handles, **kw: [])
    assert fc.generate("tweet_ids") == []


def test_generate_invalid_channel():
    with pytest.raises(ValueError):
        fc.generate("nope")


def test_fetch_numeric_ids_only_and_deduped(monkeypatch):
    class FakeResp:
        status_code = 200
        text = ('<a href="https://twitter.com/NASA/status/1899630185291212345">x</a>'
                '<a href="https://twitter.com/NASA/status/42">trop court</a>'
                '<a href="https://twitter.com/NASA/status/1899630185291212345">doublon</a>')

    monkeypatch.setattr(fc.requests, "get", lambda *a, **kw: FakeResp())
    got = fc.fetch_recent_tweet_ids(["NASA"], limit_per_handle=5)
    assert got == ["1899630185291212345"]


def test_fetch_tolerates_network_errors(monkeypatch):
    def boom(*a, **kw):
        raise fc.requests.RequestException("down")
    monkeypatch.setattr(fc.requests, "get", boom)
    assert fc.fetch_recent_tweet_ids(["NASA"]) == []
    assert fc.LAST_STATUS["saw_network_error"] is True


def test_fetch_flags_429(monkeypatch):
    class Resp429:
        status_code = 429
        text = "Rate limit exceeded"
    monkeypatch.setattr(fc.requests, "get", lambda *a, **kw: Resp429())
    assert fc.fetch_recent_tweet_ids(["NASA"]) == []
    assert fc.LAST_STATUS["saw_429"] is True


def test_fetch_passes_proxy(monkeypatch):
    seen = {}

    class FakeResp:
        status_code = 200
        text = '<a href="https://twitter.com/NASA/status/1899630185291212345">x</a>'

    def fake_get(url, **kw):
        seen.update(kw)
        return FakeResp()

    monkeypatch.setattr(fc.requests, "get", fake_get)
    fc.fetch_recent_tweet_ids(["NASA"], proxy="http://u:p@1.2.3.4:8080")
    assert seen["proxies"] == {"http": "http://u:p@1.2.3.4:8080",
                               "https": "http://u:p@1.2.3.4:8080"}


def test_cache_roundtrip_and_ttl(tmp_path):
    import json
    fc.cache_write(str(tmp_path), ["123", "456"])
    assert fc.cache_read(str(tmp_path)) == ["123", "456"]
    # ts trop ancien → expiré
    with open(fc._cache_path(str(tmp_path)), "w", encoding="utf-8") as f:
        json.dump({"ts": 0, "ids": ["999"]}, f)
    assert fc.cache_read(str(tmp_path)) == []
    # pas de cache → liste vide
    import os
    os.remove(fc._cache_path(str(tmp_path)))
    assert fc.cache_read(str(tmp_path)) == []


# ── Plan généré à partir d'une config custom (volume éditait par l'opérateur) ──

_RUN_CFG = {"duration_days": 14, "variation_min": 100, "variation_max": 100,
            "actions": {"follow": 1, "like": 1, "retweet": 0,
                        "bookmark": 0, "view": 1, "tweet": 0}}


def _plan(actions_posts=2):
    day, day_epoch = "2024-01-01", 1704067200
    content = {"users": ["someone"], "tweet_ids": ["1"], "tweets": ["hi", "yo", "gm"]}
    cfg = {**_RUN_CFG, "actions": {**_RUN_CFG["actions"], "tweet": actions_posts}}
    accounts = [f"u{i}:tok{i}" for i in range(5)]
    return farm_mod.generate_plan(day, day_epoch, accounts, cfg, content)


def test_plan_honors_custom_counts():
    plans, _ = _plan(actions_posts=2)
    for entries in plans.values():
        acc_kind = {}
        for e in entries:
            acc_kind[e["kind"]] = acc_kind.get(e["kind"], 0) + 1
        assert acc_kind.get("tweet", 0) == 2
        assert acc_kind.get("view", 0) == 1
        assert acc_kind.get("follow", 0) == 1


def test_plan_excludes_disabled_actions():
    plans, _ = _plan(actions_posts=0)
    for entries in plans.values():
        for e in entries:
            assert e["kind"] != "tweet"
