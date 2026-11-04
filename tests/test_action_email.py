"""Tests de l'action 14 « Change Email » (sans réseau) :
- mutation change_email : payload, mot de passe optionnel, échecs
- runner : pools emails.txt, validate(), exécution mode 14 (file partagée)
- /api/import-accounts : préservation des champs intermédiaires (PASS)
"""
from threading import Event

import pytest

from xbot import runner
from xbot.runner import JobStats, TargetPool, build_pools, validate
from xbot.x import actions, query_ids


# ── change_email (mutation) ───────────────────────────────────────────────────

class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class _Sess:
    """Session factice : renvoie les réponses dans l'ordre (file)."""

    def __init__(self, *resps):
        self.calls = []
        self._queue = list(resps)

    def post(self, url, payload, referer):
        self.calls.append((url, payload, referer))
        return self._queue.pop(0) if self._queue else _Resp({})


def _flow(subtasks):
    return _Resp({"data": {"flow_token": "T", "subtasks": subtasks}})


def _done():
    return _Resp({"data": {"flow_token": "T", "subtasks": [{"subtask_id": "s9"}]}})


class TestChangeEmailFlow:
    def test_full_flow_sequence(self):
        sess = _Sess(
            _flow([{"subtask_id": "s1", "enter_email": {"email": {"value": ""}}}] * 1),
            _flow([{"subtask_id": "s2", "enter_code": {"code": {"value": ""}}}]),
            _flow([{"subtask_id": "s3", "enter_password": {}}]),
            _done(),
        )
        code_seen = []

        def getter(e, g):
            code_seen.append((e, g))
            return "654321"

        assert actions.change_email(sess, "a@gmail.com", "xpw", "gpw", getter) is True
        # 1) démarrage du flow
        url0, p0, ref0 = sess.calls[0]
        assert "onboarding/task.json" in url0 and "flow_name=add_email" in url0
        assert p0 == {"input_data": {"flow_name": "add_email"}}
        assert ref0 == "https://x.com/settings/profile"
        # 2) enter_email
        assert sess.calls[1][1]["input_data"]["subtask_inputs"] == [
            {"subtask_id": "s1", "enter_email": {"email": "a@gmail.com"}}]
        assert sess.calls[1][1]["input_data"]["flow_token"] == "T"
        # 3) enter_code (code lu dans la boîte Gmail)
        assert sess.calls[2][1]["input_data"]["subtask_inputs"] == [
            {"subtask_id": "s2", "enter_code": {"code": "654321"}}]
        assert code_seen == [("a@gmail.com", "gpw")]
        # 4) enter_password (mdp du compte X)
        assert sess.calls[3][1]["input_data"]["subtask_inputs"] == [
            {"subtask_id": "s3", "enter_password": {"password": "xpw"}}]
        # 4 POST au total : start, enter_email, enter_code, enter_password ;
        # la 4e réponse (fin de flux) n'émet pas d'entrée supplémentaire.
        assert len(sess.calls) == 4

    def test_flow_no_input_subtask_ends(self):
        sess = _Sess(_done())
        assert actions.change_email(sess, "a@gmail.com", "xpw", "gpw",
                                    lambda e, g: "1") is True
        assert len(sess.calls) == 1

    def test_missing_x_password_fails_then_graphql_fallback(self):
        sess = _Sess(_flow([{"subtask_id": "s3", "enter_password": {}}]),
                     _Resp({"data": {"updateProfileEmail":
                                     {"result": {"rest_id": "1"}}}}))
        assert actions.change_email(sess, "a@gmail.com", "", "gpw",
                                    lambda e, g: "1") is True
        # 1er appel : flow ; 2e : repli GraphQL
        url, payload, _ = sess.calls[1]
        assert "graphql/" in url and url.endswith("/UpdateProfileEmail")
        assert payload["variables"] == {"email": "a@gmail.com"}
        assert payload["queryId"] == query_ids.get("UpdateProfileEmail")

    def test_http_error_both_paths(self):
        sess = _Sess(_Resp({"errors": [{}]}, status=429),
                     _Resp({"error": "x"}, status=404))
        assert actions.change_email(sess, "a@gmail.com", "p", "g",
                                    lambda e, gg: "1") is False

    def test_no_code_fails(self):
        sess = _Sess(_flow([{"subtask_id": "s2", "enter_code": {}}]))
        assert actions._change_email_flow(sess, "a@gmail.com", "p", "g",
                                          lambda e, gp: "") is False

    def test_response_ok_helper(self):
        assert actions.response_ok(_Resp({"errors": [{}]}, status=429),
                                   graphql=True) is False
        s = _Resp({"data": {"updateProfileEmail": None}}, status=200)
        assert actions.response_ok(s, graphql=True) is False


# ── runner : pools + validate ─────────────────────────────────────────────────

class TestMode14Pools:
    def test_build_pools_loads_emails(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("bot1:pw1:TOK1\nbot2:pw2:TOK2",
                                               encoding="utf-8")
        (tmp_path / "emails.txt").write_text("a@gmail.com:ga\nb@gmail.com:gb",
                                             encoding="utf-8")
        pools = build_pools(14, str(tmp_path))
        assert pools["emails"] == ["a@gmail.com:ga", "b@gmail.com:gb"]

    def test_other_mode_ignores_emails(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("bot1:TOK1", encoding="utf-8")
        (tmp_path / "tweet_ids.txt").write_text("123", encoding="utf-8")
        (tmp_path / "emails.txt").write_text("a@gmail.com", encoding="utf-8")
        assert build_pools(3, str(tmp_path))["emails"] == []

    def test_validate_empty_emails(self):
        pools = {"accounts": ["bot:TOK"], "emails": []}
        assert "No new emails" in validate(14, {}, pools)

    def test_validate_not_enough_emails(self):
        pools = {"accounts": ["b1:T1", "b2:T2"], "emails": ["a@gmail.com"]}
        msg = validate(14, {}, pools)
        assert "1 email(s) for 2 account(s)" in msg

    def test_validate_ok(self):
        pools = {"accounts": ["b1:T1"], "emails": ["a@gmail.com:ga"]}
        assert validate(14, {}, pools) == ""


# ── runner : exécution mode 14 ────────────────────────────────────────────────

class _OkSess:
    def authenticate(self):
        return True


class _NoSess:
    def authenticate(self):
        return False


POOLS = {"tweet_ids": [], "emails": ["a@gmail.com:ga", "b@gmail.com:gb"]}


class TestRunSessionMode14:
    def _calls(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            runner.actions, "change_email",
            lambda sess, email, pw="", gpw="", get_code=None:
            calls.append((email, pw)) or True)
        return calls

    def test_first_email_and_x_password(self, monkeypatch):
        calls = self._calls(monkeypatch)
        stats = JobStats("Change Email", 1)
        cfg = {"limit": 1, "_account_password": "pw1"}
        runner._run_session(_OkSess(), "bot1", 14, cfg, stats, POOLS, Event())
        assert calls == [("a@gmail.com", "pw1")]  # passe Gmail « ga » non envoyée
        assert stats.log[0]["msg"].endswith("a@gmail.com")

    def test_missing_x_password_is_empty(self, monkeypatch):
        calls = self._calls(monkeypatch)  # accounts.txt à 2 champs → ''
        runner._run_session(_OkSess(), "bot1", 14, {"limit": 1},
                            JobStats("t", 1), POOLS, Event())
        assert calls == [("a@gmail.com", "")]

    def test_shared_pool_advances(self, monkeypatch):
        calls = self._calls(monkeypatch)
        pool = TargetPool(POOLS["emails"], 1)
        s1, s2, s3 = (JobStats("t", 1) for _ in range(3))
        runner._run_session(_OkSess(), "bot1", 14, {}, s1, POOLS, Event(), pool)
        runner._run_session(_OkSess(), "bot2", 14, {}, s2, POOLS, Event(), pool)
        runner._run_session(_OkSess(), "bot3", 14, {}, s3, POOLS, Event(), pool)
        # l'ordre dans la file partagée est mélangé (shuffle) : 2 prises max
        assert sorted(c[0] for c in calls) == ["a@gmail.com", "b@gmail.com"]
        assert any("no email available" in e["msg"] for e in s3.log)

    def test_invalid_line(self, monkeypatch):
        calls = self._calls(monkeypatch)
        stats = JobStats("t", 1)
        bad = {"tweet_ids": [], "emails": [":sans-adresse"]}
        runner._run_session(_OkSess(), "bot1", 14, {}, stats, bad, Event())
        assert calls == []
        assert any("invalid line" in e["msg"] for e in stats.log)

    def test_auth_fail_consumes_nothing(self, monkeypatch):
        calls = self._calls(monkeypatch)
        pool = TargetPool(POOLS["emails"], 1)
        stats = JobStats("t", 1)
        runner._run_session(_NoSess(), "bot1", 14, {}, stats, POOLS, Event(), pool)
        assert calls == [] and pool.remaining() == 2


# ── /api/import-accounts : préservation des champs ───────────────────────────

class TestImportPreservation:
    def test_three_part_layout_keeps_password(self, client, admin_user):
        h = {"Authorization": "Bearer " + client.post(
            "/api/login", json={"username": admin_user[0],
                                "password": admin_user[1]}
        ).get_json()["token"]}
        r = client.post("/api/import-accounts", json={
            "fields": ["USER", "PASS", "AUTH_TOKEN"],
            "separator": ":", "mode": "replace",
            "content": "bot1:pw1:TOK1\nbot2:pw2:TOK2\n",
        }, headers=h)
        assert r.status_code == 200 and r.get_json()["imported"] == 2
        content = client.get("/api/file/accounts.txt", headers=h).get_json()["content"]
        lines = [ln for ln in content.splitlines() if ln.strip()]
        assert lines == ["bot1:pw1:TOK1", "bot2:pw2:TOK2"]
        # sémantique du runner : [0] = username, [-1] = auth_token
        assert [ln.split(":")[0] for ln in lines] == ["bot1", "bot2"]
        assert [ln.split(":")[-1] for ln in lines] == ["TOK1", "TOK2"]

    def test_two_part_layout_still_works(self, client, admin_user):
        h = {"Authorization": "Bearer " + client.post(
            "/api/login", json={"username": admin_user[0],
                                "password": admin_user[1]}
        ).get_json()["token"]}
        client.post("/api/import-accounts", json={
            "fields": ["USER", "AUTH_TOKEN"], "separator": ":", "mode": "replace",
            "content": "bot1:TOK1",
        }, headers=h)
        content = client.get("/api/file/accounts.txt", headers=h).get_json()["content"]
        assert content.strip() == "bot1:TOK1"
