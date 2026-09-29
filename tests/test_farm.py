"""Tests du moteur de ferme (réchauffement autonome / humanisation) :
- mutate_text        : mutation de contenu organique
- generate_plan      : budgets Poisson, fenêtre active, jours de repos
- humanization_score : formule exacte (40/20/20/10/10)
- FarmState          : persistance redémarrage
- FarmRunner        : validations de démarrage + forme des scores
"""
import json
import time

import pytest

from xbot.farm import (AUTH_FAIL_TRIP, ACTION_KINDS, DEPTH_TARGET,
                       GROWTH_TARGET, VIS_WINDOW, FarmRunner, FarmState,
                       active_days, estimate_ready_days, generate_plan,
                       humanization_score, mutate_text, score_label,
                       validate_farm_cfg)


HOUR = 3600
# config custom d'une journée de vie (mêmes clés que validate_farm_cfg)
DEFAULT_CFG = {
    "duration_days": 14,
    "variation_min": 80,
    "variation_max": 100,
    "actions": {"follow": 1, "like": 2, "retweet": 1,
                "bookmark": 1, "view": 2, "tweet": 1},
}


def _content(**kw):
    c = {"accounts": [], "usernames": set(), "users": [], "tweet_ids": [], "tweets": []}
    c.update(kw)
    return c


def _state(**kw):
    return {"vis": [], "ok_ts": [], "auth_fail_ts": [], "followers": 0,
            "followers_at_start": 0, "status": "dormant", "done": {}, **kw}


class TestMutateText:
    def test_spintax_choice(self):
        outs = {mutate_text("{hello|bonjour|hey} world") for _ in range(60)}
        assert any(o.startswith("hello") for o in outs)
        assert any(o.startswith("bonjour") for o in outs)
        assert any(o.startswith("hey") for o in outs)
        assert all("world" in o for o in outs)
        assert all("{" not in o and "}" not in o for o in outs)

    def test_variety(self):
        raw = "une belle journée {en perspective|devant soi} 🙌"
        outs = {mutate_text(raw) for _ in range(100)}
        assert len(outs) > 5  # spintax × emoji-ride × ponctuation

    def test_empty_and_passthrough(self):
        assert mutate_text("") == ""
        out = mutate_text("texte fixe sans variantes")
        assert out.startswith("texte fixe sans variantes")

    def test_support_text_pool_duplication_prevention(self):
        # la même ligne génère des textes distincts sur n appels
        outs = {mutate_text("gm") for _ in range(200)}
        assert len(outs) >= 2  # au moins suffixe emoji présent/absent



class TestGeneratePlan:
    DAY, EPOCH = "2030-01-01", 1893456000.0

    def _cfg(self, **kw):
        c = dict(DEFAULT_CFG, actions=dict(DEFAULT_CFG["actions"]))
        for k, v in kw.items():
            if k in c["actions"]:
                c["actions"][k] = v
            else:
                c[k] = v
        return c

    def _zero_cfg(self, variation=100, **actions):
        """cfg avec uniquement les actions nommées > 0 (autres = 0)."""
        return {"duration_days": 14,
                "variation_min": variation, "variation_max": variation,
                "actions": {k: actions.get(k, 0) for k in ACTION_KINDS}}

    def _zero_cfg(self, variation=100, **actions):
        """cfg avec uniquement les actions passées en kw (autres = 0)."""
        return {"duration_days": 14,
                "variation_min": variation, "variation_max": variation,
                "actions": {k: actions.get(k, 0) for k in ACTION_KINDS}}

    def _accounts(self, n=3):
        return [f"bot{i}:tok{i}" for i in range(n)]

    def _content_full(self):
        return _content(accounts=self._accounts(),
                        usernames={"bot0", "bot1", "bot2"},
                        users=[f"t{i}" for i in range(10)],
                        tweet_ids=[f"tweet_{i}" for i in range(40)],
                        tweets=[f"raw_{i}" for i in range(5)])

    def test_per_action_counts_exact_at_100pct(self):
        # 100 % exact : le plan compte chaque action exactement comme configuré,
        # pour CHAQUE compte, SANS variation
        c = self._content_full()
        used = {}
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"],
                                 self._cfg(variation_min=100, variation_max=100), c, used)
        for entries in plans.values():
            by_kind = {}
            for e in entries:
                by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
            assert by_kind == {"follow": 1, "like": 2, "retweet": 1,
                               "bookmark": 1, "view": 2, "tweet": 1}

    def test_window_bounds(self):
        c = self._content_full()
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"], self._cfg(), c, {})
        for entries in plans.values():
            for e in entries:
                assert self.EPOCH <= e["ts"] <= self.EPOCH + 86400
                assert e["status"] == "pending"
                assert e["kind"] in ACTION_KINDS
                assert e["detail"] == ""

    def test_sorted_and_ids_unique(self):
        c = self._content_full()
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"], self._cfg(), c, {})
        for entries in plans.values():
            ts = [e["ts"] for e in entries]
            assert ts == sorted(ts)
            ids = [e["id"] for e in entries]
            assert len(set(ids)) == len(ids)

    def test_variation_scales_counts_within_bounds(self):
        # 1–100 % : les comptes totaux restent ≤ la somme exacte, jamais négatifs
        c = self._content_full()
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"],
                                 self._cfg(variation_min=1, variation_max=60), c, {})
        nominal = sum(DEFAULT_CFG["actions"].values())
        for entries in plans.values():
            assert 0 <= len(entries) <= nominal

    def test_no_repeat_within_and_across_calls(self):
        # `used` persistant par compte : jamais deux fois la même cible pour le
        # MÊME compte sur le run (jour 1 ∩ jour 2 = ∅)
        c = _content(accounts=self._accounts(), users=["t1", "t2", "t3"],
                     tweet_ids=["314", "271"], tweets=["alpha", "beta"])
        cfg = self._cfg(variation_min=100, variation_max=100,
                        follow=1, like=1, retweet=1, bookmark=0, view=0, tweet=1)
        used = {}
        plans1, _ = generate_plan("2030-01-01", 1893456000.0, c["accounts"], cfg, c, used)
        plans2, _ = generate_plan("2030-01-02", 1893456000.0 + 86400, c["accounts"], cfg, c, used)
        for user, entries1 in plans1.items():
            day1 = {e["target"] for e in entries1}
            day2 = {e["target"] for e in plans2[user]}
            assert day1.isdisjoint(day2)
        assert all(any(e["target"] for e in v) for v in plans1.values())

    def test_content_gating(self):
        # canal vide → action absente du plan même si configurée
        c = _content(accounts=self._accounts(), users=[], tweet_ids=["123"], tweets=[])
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"], self._cfg(), c, {})
        for entries in plans.values():
            for e in entries:
                assert e["kind"] not in ("follow", "tweet")

    def test_follow_never_self_or_sibling(self):
        # cible = compte de la ferme : la pool follow l'exclut ; si c'est la
        # seule cible → plus de follow du tout
        c = _content(accounts=self._accounts(), usernames={"bot0"},
                     users=["bot0"], tweet_ids=["123"], tweets=[])
        used = {}
        plans, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"],
                                 self._cfg(variation_min=100, variation_max=100), c, used)
        for entries in plans.values():
            for e in entries:
                assert e["kind"] != "follow" or e["target"] != "bot0"

    def test_exhausted_pools_reported(self):
        # SEULE l'action follow est configurée ; pool = 1 cible, besoin = 5 : jour 1 = 1 cible,
        # jour 2 = 0 cible ET 1 signalement d'épuisement par compte
        c = _content(accounts=self._accounts(), users=["seule"],
                     tweet_ids=["123"], tweets=[])
        cfg = self._zero_cfg(follow=5)
        used = {}
        plans1, _ = generate_plan(self.DAY, self.EPOCH, c["accounts"], cfg, c, used)
        for entries in plans1.values():
            assert len(entries) == 1 and entries[0]["kind"] == "follow"
        plans2, exhausted2 = generate_plan(self.DAY, self.EPOCH, c["accounts"], cfg, c, used)
        for entries in plans2.values():
            assert len(entries) == 0
        assert sorted(exhausted2) == [("follow", u) for u in ("bot0", "bot1", "bot2")]


class TestFarmCfgValidation:
    def test_duration_required_and_bounded(self):
        _, err = validate_farm_cfg({"duration_days": 0, "actions": {"view": 1}})
        assert "duration_days" in err
        _, err = validate_farm_cfg({"duration_days": 400, "actions": {"view": 1}})
        assert "365" in err
        assert not validate_farm_cfg({"duration_days": 14, "actions": {"view": 1}})[1]

    def test_at_least_one_action_and_bounds(self):
        _, err = validate_farm_cfg({"duration_days": 14, "actions": {"view": 0, "like": 0}})
        assert "at least one" in err
        _, err = validate_farm_cfg({"duration_days": 14, "actions": {"view": 101}})
        assert "100" in err

    def test_variation_min_le_max(self):
        _, err = validate_farm_cfg({"duration_days": 14,
                                    "variation_min": 90, "variation_max": 60,
                                    "actions": {"view": 1}})
        assert "variation" in err

    def test_counts_must_be_non_negative_ints(self):
        _, err = validate_farm_cfg({"duration_days": 14, "actions": {"view": -1}})
        assert err
        _, err = validate_farm_cfg({"duration_days": 14, "actions": {"view": 2.5}})
        assert err


class TestActiveDays:
    def test_counts_distinct_buckets(self):
        st = {"ok_ts": [1000, 1000 + 100, 1000 + 86400, 1000 + 3 * 86400]}
        assert active_days(st) == 3
        assert active_days({"ok_ts": []}) == 0


class TestEstimate:
    NOW = 100 * 86400.0

    def _st(self, **kw):
        d = {"vis": [], "ok_ts": [], "auth_fail_ts": []}
        d.update(kw)
        return d

    def test_ready_now_is_zero_eta(self):
        st = self._st(
            vis=[True] * 3,
            ok_ts=[self.NOW - 86400 + k * 3600 for k in range(5)],
            followers=GROWTH_TARGET, followers_at_start=0,
        )
        st["ok_ts"] += [self.NOW - d * 86400 for d in range(1, DEPTH_TARGET + 1)]
        eta, note = estimate_ready_days(st, True, self.NOW)
        assert eta is not None and eta < 1 and note == ""

    def test_compromised(self):
        st = self._st(status="compromised")
        eta, note = estimate_ready_days(st, True, self.NOW)
        assert eta is None and note == "compromised"

    def test_hidden_posts_block(self):
        st = self._st(
            vis=[False] * 3,
            ok_ts=[self.NOW - 3600],
            followers=0, followers_at_start=0,
        )
        eta, note = estimate_ready_days(st, True, self.NOW)
        assert eta is None and note == "posts hidden"

    def test_depth_alone_can_suffice_without_followers(self):
        # 40 (vis) + 10 (profil) + 10 (intégrité) + profondeur → ≥ 70 même
        # sans aucun follower : l'ETA reste calculable.
        st = self._st(ok_ts=[self.NOW - 3600], followers=0, followers_at_start=0)
        eta, note = estimate_ready_days(st, True, self.NOW)
        assert eta is not None and note == "" and eta > 0

    def test_no_growth_no_projection_when_points_missing(self):
        # profil incomplet + échecs d'auth (lock=0) + aucun follower :
        # même saturé, la trajectoire n'atteint pas 70.
        st = self._st(
            auth_fail_ts=[self.NOW - 100, self.NOW - 60, self.NOW - 30],
            followers=0, followers_at_start=0,
        )
        eta, note = estimate_ready_days(st, False, self.NOW)
        assert eta is None and note == "no follower growth"

    def test_converges_on_healthy_trajectory(self):
        st = self._st(
            vis=[True],
            ok_ts=[self.NOW - 3 * 86400 + k * 3600 for k in range(6)],
            followers=12, followers_at_start=0,
        )
        eta, note = estimate_ready_days(st, True, self.NOW)
        assert eta is not None and note == "" and eta > 0

    def test_eta_is_profile_independent(self):
        # sans notion de profil, deux runs d'une même trajectoire donnent le
        # même ETA — le moteur est déterministe, plus de facteur profil
        st = self._st(
            vis=[True],
            ok_ts=[self.NOW - 86400 + k * 3600 for k in range(6)],
            followers=10, followers_at_start=0,
        )
        e1, _ = estimate_ready_days(st, True, self.NOW)
        e2, _ = estimate_ready_days(st, True, self.NOW)
        assert e1 is not None and e2 is not None and e1 == e2


class TestScore:
    BASE = {"vis": [], "ok_ts": [], "auth_fail_ts": []}

    def _st(self, **kw):
        d = dict(self.BASE); d.update(kw); return d

    def test_flat_perfect(self):
        st = self._st(
            vis=[True] * VIS_WINDOW,
            ok_ts=[1000 + k * 86400 for k in range(DEPTH_TARGET + 5)],
            followers=GROWTH_TARGET + 5, followers_at_start=0,
        )
        s = humanization_score(st, time.time() - 100 * 86400, True)
        assert s == 100

    def test_flat_zero(self):
        st = self._st(followers=0, followers_at_start=0)
        assert humanization_score(st, time.time(), False) == 0

    def test_exact_partials(self):
        st = self._st(
            vis=[True] * 25 + [False] * 25,          # 25/50 visible → 20 pts
            ok_ts=[1000 + k * 86400 for k in range(7)],  # 7/14 → 10 pts
            followers=25, followers_at_start=0,      # 25/50 → 10 pts
        )
        s = humanization_score(st, time.time(), True)   # +10 profil +10 lock
        assert s == 60

    def test_auth_fail_trip_kills_lock_points(self):
        st = self._st(
            vis=[True] * VIS_WINDOW,
            ok_ts=[1000 + k * 86400 for k in range(14)],
            followers=60, followers_at_start=0,
            auth_fail_ts=[time.time()] * AUTH_FAIL_TRIP,
        )
        s = humanization_score(st, time.time(), True)
        assert s == 90  # lock 10 pts perdus

    def test_labeling(self):
        assert score_label(100, "ok") == "ready"
        assert score_label(70, "ok") == "ready"
        assert score_label(40, "ok") == "warming"
        assert score_label(10, "ok") == "dormant"
        assert score_label(100, "compromised") == "compromised"


class TestStatePersistence:
    def test_round_trip(self, tmp_path):
        p = str(tmp_path / "state.json")
        s1 = FarmState(p)
        s1.load()
        acc = s1.account("bot0")
        acc["vis"] = [True, False, True]
        acc["followers"] = 33
        acc["followers_at_start"] = 21
        acc["auth_fail_ts"] = [time.time()]
        s1.save()

        s2 = FarmState(p)
        s2.load()
        acc2 = s2.account("bot0")
        assert acc2["vis"] == [True, False, True]
        assert acc2["followers"] == 33
        assert acc2["followers_at_start"] == 21
        assert acc2["auth_fail_ts"]

    def test_vis_window_bounded(self, tmp_path):
        s = FarmState(str(tmp_path / "state.json"))
        s.load()
        acc = s.account("bot0")
        acc["vis"] = list(range(VIS_WINDOW + 100))
        acc2 = s.account("bot0")
        assert len(acc2["vis"]) == VIS_WINDOW


class TestRunnerValidation:
    RUN_CFG = {"duration_days": 14, "variation_min": 80, "variation_max": 100,
               "actions": {"view": 1}}

    def test_start_refuses_empty_accounts(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("")
        f = FarmRunner(base_dir=str(tmp_path))
        assert "No X accounts imported" in f.start(self.RUN_CFG)

    def test_start_refuses_invalid_cfg(self, tmp_path):
        # validation de la config custom AVANT tout accès canal
        (tmp_path / "accounts.txt").write_text("bot:tok\n")
        f = FarmRunner(base_dir=str(tmp_path))
        assert "duration_days" in f.start({"actions": {"view": 1}})

    def test_start_refuses_no_content(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("bot:tok\n")
        for name in ("users.txt", "tweet_ids.txt", "tweets.txt"):
            (tmp_path / name).write_text("")
        f = FarmRunner(base_dir=str(tmp_path))
        assert "Fill the Life content channels" in f.start(self.RUN_CFG)

    def test_start_and_stop_strings(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("bot:tok\n")
        (tmp_path / "users.txt").write_text("victime\n")
        (tmp_path / "tweet_ids.txt").write_text("123\n")
        (tmp_path / "tweets.txt").write_text('[{"text":"gm"}]\n')
        f = FarmRunner(base_dir=str(tmp_path))
        assert f.start(self.RUN_CFG) == ""
        assert f.start(self.RUN_CFG) == "Farm is already running"
        assert f.stop() == ""
        # le thread sort vite après l'événement d'arrêt (≤ ~1 s)
        for _ in range(100):
            if not f.running:
                break
            time.sleep(0.02)
        assert not f.running
        assert f.stop() == "No farm running"

    def test_scores_shape(self, tmp_path):
        (tmp_path / "accounts.txt").write_text("bot:tok\n")
        (tmp_path / "users.txt").write_text("victime\n")
        (tmp_path / "tweet_ids.txt").write_text("123\n")
        (tmp_path / "tweets.txt").write_text('[{"text":"gm {a|b}}"]\n')
        f = FarmRunner(base_dir=str(tmp_path))
        s = f.scores()
        assert set(s.keys()) == {"running", "accounts"}
        a = s["accounts"][0]
        for k in ("account", "score", "label", "followers", "growth",
                  "active_days", "tweets_ok", "tweets_flagged", "status"):
            assert k in a
        assert a["account"] == "bot"
        assert a["label"] == "dormant"
        assert a["score"] == 0


class _NullSession:
    """Session factice sans réseau : échec « proxy/network », non compté
    dans la santé du compte — permet de tick() sans budget réseau."""
    def __init__(self, **kw):
        self.last_net_error = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def authenticate(self):
        return False


class TestEngineTelemetry:
    def _farm(self, tmp_path, monkeypatch):
        (tmp_path / "accounts.txt").write_text("bot0:tok0\n")
        (tmp_path / "users.txt").write_text("victime\n")
        (tmp_path / "tweet_ids.txt").write_text("123\n")
        (tmp_path / "tweets.txt").write_text('[{"text":"gm"}]\n')
        import xbot.farm as farm_mod
        monkeypatch.setattr(farm_mod, "XSession", _NullSession)
        return FarmRunner(base_dir=str(tmp_path))

    def test_plan_log_and_engine_waiting(self, tmp_path, monkeypatch):
        f = self._farm(tmp_path, monkeypatch)
        day, day_epoch, now = f._today()
        f.state.data["cfg"] = {"duration_days": 14, "variation_min": 80, "variation_max": 100, "actions": {"follow": 1, "view": 1, "tweet": 1}}
        f._tick()
        eng = f.state.data["engine"]
        assert eng["reason"] in ("waiting", "")
        assert eng["last_tick"] > 0
        assert eng["planned"] > 0            # plan du jour généré
        assert any(l["msg"].startswith(f"plan {day}:") for l in f.log)

    def test_waiting_next_due_and_plan_exhausted(self, tmp_path, monkeypatch):
        f = self._farm(tmp_path, monkeypatch)
        day, day_epoch, now = f._today()
        hi = day_epoch + 86400
        f.state.data["cfg"] = {"duration_days": 14, "variation_min": 80, "variation_max": 100, "actions": {"follow": 1, "view": 1, "tweet": 1}}
        fut = min(now + 3600, hi - 1)
        past_ok = max(day_epoch, now - 3600)
        f.state.data["plans"] = {day: {"bot0": [
            {"id": "a", "ts": past_ok, "kind": "view", "status": "ok", "detail": ""},
            {"id": "b", "ts": fut, "kind": "view", "status": "pending", "detail": ""}]}}
        f._tick()
        eng = f.state.data["engine"]
        assert (eng["reason"], eng["done"], eng["pending"]) == ("waiting", 1, 1)
        assert eng["next_due"] == fut
        # plan du jour terminé
        f.state.data["plans"][day]["bot0"][1]["status"] = "ok"
        f._tick()
        assert f.state.data["engine"]["reason"] == "plan_exhausted"

    def test_compromised_reason_and_no_accounts(self, tmp_path, monkeypatch):
        f = self._farm(tmp_path, monkeypatch)
        day, day_epoch, now = f._today()
        f.state.data["cfg"] = {"duration_days": 14, "variation_min": 80, "variation_max": 100, "actions": {"follow": 1, "view": 1, "tweet": 1}}
        st = f.state.account("bot0")
        st["auth_fail_ts"] = [now, now, now]  # 3 échecs → compromised
        f.state.data["plans"] = {day: {"bot0": [
            {"id": "a", "ts": now + 600, "kind": "view", "status": "pending", "detail": ""}]}}
        f._tick()
        assert f.state.data["engine"]["reason"] == "no_active_accounts"
        # sans aucun compte : raison dédiée
        (tmp_path / "accounts.txt").write_text("")
        f2 = FarmRunner(base_dir=str(tmp_path))
        f2._tick()
        assert f2.state.data["engine"]["reason"] == "no_accounts"

    def test_invalid_cfg_reports_reason(self, tmp_path, monkeypatch):
        # config héritée d'ancien format (ex. {"profile": "fast"}) : raison dédiée,
        # aucun plan généré
        f = self._farm(tmp_path, monkeypatch)
        day, _, _ = f._today()
        f.state.data["cfg"] = {"profile": "fast"}
        f._tick()
        assert f.state.data["engine"]["reason"] == "invalid_cfg"
        assert "plans" not in f.state.data or day not in f.state.data.get("plans", {})

    def test_duration_completion_stops_run(self, tmp_path, monkeypatch):
        # run dont la durée est écoulée : tick marque completed, arrête le moteur
        f = self._farm(tmp_path, monkeypatch)
        f.stop_event.clear()
        f.running = True
        f.state.data["cfg"] = {"duration_days": 14, "variation_min": 80,
                               "variation_max": 100, "actions": {"view": 1}}
        f.state.data["run"] = {"duration_days": 1,
                               "start": time.time() - 2 * 86400,
                               "completed": False}
        f.state.data["running"] = True
        f._tick()
        assert f.state.data["run"]["completed"] is True
        assert f.state.data["engine"]["reason"] == "completed"
        assert f.state.data["engine"]["next_due"] is None
        assert f.stop_event.is_set()
        assert f.state.data["running"] is False

    def test_completed_run_stays_inert(self, tmp_path, monkeypatch):
        # un run déjà complété : le tick devient inerte (aucun plan régénéré)
        f = self._farm(tmp_path, monkeypatch)
        day, day_epoch, _ = f._today()
        f.state.data["cfg"] = {"duration_days": 14, "variation_min": 80,
                               "variation_max": 100, "actions": {"view": 1}}
        f.state.data["run"] = {"duration_days": 1, "start": 0, "completed": True}
        f._tick()
        assert "plans" not in f.state.data or day not in f.state.data.get("plans", {})
        assert f.stop_event.is_set()

    def test_heartbeat_message_shapes(self, tmp_path, monkeypatch):
        f = self._farm(tmp_path, monkeypatch)
        now = time.time()
        f.log.clear()  # > 30 min sans message
        f.state.data["engine"] = {"last_tick": now, "planned": 5, "done": 2,
                                  "reason": "waiting", "next_due": now + 3000}
        f._heartbeat()
        msg = f.log[-1]["msg"]
        assert "engine alive" in msg and "2/5" in msg and "next action in ~" in msg
        # pas de fuite de détail : raison inconnue → texte propre
        f.state.data["engine"]["reason"] = "???"; f.log.clear()
        f._heartbeat()
        assert "???" not in f.log[-1]["msg"]

    def test_status_exposes_engine_and_now(self, tmp_path, monkeypatch):
        f = self._farm(tmp_path, monkeypatch)
        f.state.data["engine"] = {"last_tick": 1.0, "planned": 3, "done": 1,
                                  "pending": 2, "failed": 0, "next_due": 99.0,
                                  "reason": "waiting"}
        s = f.status()
        assert s["engine"]["reason"] == "waiting"
        assert s["engine"]["planned"] == 3
        assert abs(s["now"] - time.time()) < 5
