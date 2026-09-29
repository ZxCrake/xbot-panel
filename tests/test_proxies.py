"""Multi-proxy : parsing, session épinglée (rotating), résolution par compte,
validation de la config, et exemptions de santé de compte côté ferme/runner.
"""
import json
from threading import Event

import pytest

from xbot import proxies
from xbot.farm import AUTH_FAIL_TRIP, FarmRunner
from xbot.proxies import (SESSION_MARKER, parse_proxy_list, resolve_for_account,
                          resolve_for_fetch, validate_proxy_line)
from xbot.security import validate_config


class TestParseProxyList:
    def test_multi_line_comments_and_blank(self):
        text = "# commentaire\n\nuser:pass@h1:7777\n  http://u:p@h2:1080 \n"
        assert parse_proxy_list(text) == ["user:pass@h1:7777", "http://u:p@h2:1080"]

    def test_rejects_whitespace_in_line(self):
        with pytest.raises(ValueError):
            parse_proxy_list("user:pass @host:1")

    def test_rejects_bad_scheme(self):
        with pytest.raises(ValueError):
            validate_proxy_line("ftp://h:21")

    def test_accepts_forms_and_schemes(self):
        for line in ("u:p@h:1", "http://u:p@h:1", "https://h:1", "socks5://h:1",
                     "socks5h://u:p@h:1", "h:8080", "h", "[2001:db8::1]:8080"):
            validate_proxy_line(line)

    def test_rejects_malformed(self):
        for line in ("u:p@", "u:p@h:1:2", "", "x" * 513):
            with pytest.raises(ValueError):
                validate_proxy_line(line)

    def test_max_lines(self):
        with pytest.raises(ValueError):
            parse_proxy_list("\n".join(["h:1"] * 1001))


_CFG = {
    "proxy": "shared:s3cr3t@fallback:9000",
    "proxies": "uA:pA@gateway-a:7777\nuB:pB@gateway-b:7777",
    "proxy_mode": "static",
    "proxy_session_epoch": 0,
}


class TestResolveForAccount:
    def test_static_index_alignment(self):
        assert resolve_for_account(_CFG, 0) == "http://uA:pA@gateway-a:7777"
        assert resolve_for_account(_CFG, 1) == "http://uB:pB@gateway-b:7777"

    def test_static_spillover_uses_fallback(self):
        assert resolve_for_account(_CFG, 2) == "http://shared:s3cr3t@fallback:9000"

    def test_no_proxy_configured(self):
        assert resolve_for_account({"proxy": "", "proxies": ""}, 0) == ""

    def test_rotating_pins_sticky_session(self):
        cfg = {**_CFG, "proxy_mode": "rotating"}
        p0 = resolve_for_account(cfg, 0)
        assert p0.startswith("http://uA:pA-session-")
        assert SESSION_MARKER in p0
        # stable for the same slot within the same epoch
        assert resolve_for_account(cfg, 0) == p0

    def test_rotating_session_distinct_per_slot(self):
        cfg = {**_CFG, "proxy_mode": "rotating"}
        p0, p1 = resolve_for_account(cfg, 0), resolve_for_account(cfg, 1)
        sid0 = p0.rsplit(SESSION_MARKER, 1)[1].split("@")[0]
        sid1 = p1.rsplit(SESSION_MARKER, 1)[1].split("@")[0]
        assert sid0 != sid1 and len(sid0) == 16 and p0 != p1

    def test_rotating_epoch_bump_rotates_all_ids(self):
        cfg0 = {**_CFG, "proxy_mode": "rotating", "proxy_session_epoch": 0}
        cfg1 = {**cfg0, "proxy_session_epoch": 41}
        assert resolve_for_account(cfg0, 0) != resolve_for_account(cfg1, 0)
        assert resolve_for_account(cfg0, 1) != resolve_for_account(cfg1, 1)

    def test_rotating_preserves_manual_session_marker(self):
        manual = "u-session-mine-sessionduration-30:p@g:7777"
        cfg = {"proxy": "", "proxies": manual, "proxy_mode": "rotating",
               "proxy_session_epoch": 0}
        assert resolve_for_account(cfg, 0) == "http://" + manual

    def test_rotating_ip_allowlisted_gateway_unchanged(self):
        cfg = {"proxy": "", "proxies": "gate.example:7777",
               "proxy_mode": "rotating", "proxy_session_epoch": 0}
        assert resolve_for_account(cfg, 0) == "http://gate.example:7777"

    def test_scheme_preserved(self):
        cfg = {**_CFG, "proxies": "socks5h://u:p@g:1080"}
        assert resolve_for_account(cfg, 0).startswith("socks5h://")

    def test_invalid_fallback_yields_direct(self):
        cfg = {**_CFG, "proxies": "", "proxy": "not a proxy !!"}
        assert resolve_for_account(cfg, 5) == ""


class TestResolveForFetch:
    def test_rotating_first_line_raw_no_pin(self):
        # fetches anonymes : IP fraîche à chaque requête — pas de session épinglée
        out = resolve_for_fetch({**_CFG, "proxy_mode": "rotating"})
        assert out == "http://uA:pA@gateway-a:7777"
        assert SESSION_MARKER not in out

    def test_fallback_to_shared(self):
        assert resolve_for_fetch({**_CFG, "proxies": ""}) == \
            "http://shared:s3cr3t@fallback:9000"

    def test_empty(self):
        assert resolve_for_fetch({"proxy": "", "proxies": ""}) == ""


class TestValidateConfigProxies:
    def test_accepts_proxy_fields(self):
        out = validate_config({"proxies": _CFG["proxies"], "proxy_mode": "rotating",
                               "proxy_session_epoch": 3})
        assert out["proxy_mode"] == "rotating"
        assert out["proxy_session_epoch"] == 3

    def test_rejects_bad_mode(self):
        with pytest.raises(ValueError):
            validate_config({"proxy_mode": "turbo"})

    def test_rejects_bad_line_with_prefix(self):
        with pytest.raises(ValueError, match="proxies:"):
            validate_config({"proxies": "ok:ok@h:1\nbad line here"})

    def test_rejects_bad_shared_proxy(self):
        with pytest.raises(ValueError):
            validate_config({"proxy": "u:p@h:1:2"})

    def test_accepts_empty_shared_proxy(self):
        out = validate_config({"proxy": ""})
        assert out["proxy"] == ""

    def test_epoch_bounds(self):
        with pytest.raises(ValueError):
            validate_config({"proxy_session_epoch": -1})


# ── intégration ferme / runner ──────────────────────────────────────────────

def _farm(tmp_path, proxies_text="", mode="static", epoch=0, shared=""):
    (tmp_path / "accounts.txt").write_text("bot0:tok0\nbot1:tok1\n")
    (tmp_path / "config.json").write_text(json.dumps(
        {"proxy_mode": mode, "proxy_session_epoch": epoch,
         "proxies": proxies_text, "proxy": shared}))
    return FarmRunner(base_dir=str(tmp_path))


class _FakeSession:
    """Enregistre les kwargs du constructeur ; échec d'auth configurable."""
    net_error = False
    captured = []

    def __init__(self, **kw):
        self.last_net_error = type(self).net_error
        type(self).captured.append(kw)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def authenticate(self):
        return False


@pytest.fixture
def fake_session(monkeypatch):
    _FakeSession.captured = []
    _FakeSession.net_error = False
    monkeypatch.setattr(proxies, "resolve_for_account", proxies.resolve_for_account)  # sanity
    import xbot.farm as farm_mod
    import xbot.runner as runner_mod
    monkeypatch.setattr(farm_mod, "XSession", _FakeSession)
    monkeypatch.setattr(runner_mod, "XSession", _FakeSession)
    return _FakeSession


class TestFarmProxyBehavior:
    CONTENT = {"accounts": ["bot0:tok0", "bot1:tok1"]}

    def test_per_account_proxy_resolution_and_net_error_exempt(self, tmp_path, fake_session):
        f = _farm(tmp_path, proxies_text="u:p@g0:7777", shared="s:pp@fb:9")
        entry = {"kind": "tweet", "status": "pending"}
        fake_session.net_error = True
        f._execute("bot1:tok1", entry, self.CONTENT)
        # bot1 → index 1 → pas de ligne 2 → fallback partagé
        assert fake_session.captured[0]["proxy"] == "http://s:pp@fb:9"
        # erreur transport : PAS comptée dans la santé du compte
        assert entry["detail"] == "proxy/network error"
        st = f.state.account("bot1")
        assert st["auth_fail_ts"] == []
        assert st["status"] != "compromised"

    def test_auth_failure_counted_then_compromised(self, tmp_path, fake_session):
        f = _farm(tmp_path)
        st_detail = ""
        for _ in range(AUTH_FAIL_TRIP):
            entry = {"kind": "tweet", "status": "pending"}
            f._execute("bot0:tok0", entry, self.CONTENT)
            st_detail = entry["detail"]
        st = f.state.account("bot0")
        assert len(st["auth_fail_ts"]) == AUTH_FAIL_TRIP
        assert st["status"] == "compromised"
        assert st_detail == "auth failed"

    def test_farm_runtime_proxy_rotating_pins_session(self, tmp_path):
        f = _farm(tmp_path, proxies_text="u:p@g0:7777", mode="rotating")
        assert f._runtime_proxy(0).startswith("http://u:p-session-")


class TestRunnerProxyResolution:
    def test_account_index_from_cfg_picks_line(self, monkeypatch, fake_session):
        import xbot.runner as runner
        cfg = {"proxy": "", "proxy_mode": "rotating", "proxy_session_epoch": 0,
               "proxies": "uA:pA@ga:1\nuB:pB@gb:2", "_account_index": 1}
        stats = runner.JobStats("t", 2)
        runner.run_account("demoB:tok", 3, cfg, stats, {}, Event())
        assert fake_session.captured[-1]["proxy"].startswith("http://uB:pB-session-")

    def test_missing_account_index_defaults_to_line_zero(self, fake_session):
        import xbot.runner as runner
        cfg = {"proxy": "", "proxy_mode": "rotating", "proxy_session_epoch": 0,
               "proxies": "uA:pA@ga:1\nuB:pB@gb:2"}
        stats = runner.JobStats("t", 2)
        runner.run_account("demoA:tok", 3, cfg, stats, {}, Event())
        assert fake_session.captured[-1]["proxy"].startswith("http://uA:pA-session-")
