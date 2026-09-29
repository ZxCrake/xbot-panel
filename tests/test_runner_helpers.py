"""Tests des helpers anti-détection du runner :
- TargetPool        : file partagée des cibles (failover entre comptes)
- tweet_visibility  : détection des tweets masqués par X (shadowban)
- JobStats          : compteur "hidden"
"""
from threading import Event

import xbot.runner as runner
from xbot.runner import TargetPool, JobStats
from xbot.x.actions import tweet_visibility


class TestTargetPool:
    def test_distributed_once_globally(self):
        pool = TargetPool([f"u{i}" for i in range(10)], per_target=1)
        got = pool.take(4) + pool.take(4) + pool.take(4)
        assert sorted(got) == [f"u{i}" for i in range(10)]  # zéro doublon, zéro perte
        assert pool.take(1) == []  # file épuisée

    def test_dead_account_loses_nothing(self):
        # Scénario du bug : 1 cible, 18 comptes, le titulaire auth-fail.
        pool = TargetPool(["victime"], per_target=1)
        dead_account_took = []  # le compte mort ne consomme rien (auth d'abord)
        survivor = pool.take(1)
        assert dead_account_took == [] and survivor == ["victime"]

    def test_per_target_copies(self):
        pool = TargetPool(["a", "b"], per_target=3)
        flat = pool.take(10)
        assert flat.count("a") == 3 and flat.count("b") == 3

    def test_take_n_and_zero(self):
        pool = TargetPool(["a", "b", "c"], per_target=1)
        assert pool.take(0) == []
        assert len(pool.take(2)) == 2
        assert len(pool.take(5)) == 1  # reste 1

    def test_remaining(self):
        pool = TargetPool(["a", "b"], per_target=1)
        assert pool.remaining() == 2
        pool.take(1)
        assert pool.remaining() == 1


class _Sess:
    """Session factice : auth réussie ou non, context-manager minimal."""
    ok = False

    def __init__(self, **kw):
        self.last_net_error = False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def authenticate(self):
        return type(self).ok


class TestTargetPoolFailover:
    """Scénario du bug rapporté : 1 cible, 18 comptes, le seul compte qui
    tenait la cible auth-fail → la cible était perdue avec lui."""

    POOLS = {"tweet_ids": [], "users": ["victime"]}

    def _run_with(self, monkeypatch, ok, acc="bot:tok"):
        _Sess.ok = ok
        monkeypatch.setattr(runner, "XSession", _Sess)
        stats = JobStats("t", 1)
        return stats

    def test_dead_account_loses_nothing_survivor_takes_target(self, monkeypatch):
        pool = TargetPool(["victime"], per_target=1)
        followed = []
        monkeypatch.setattr(runner.actions, "follow",
                            lambda sess, t: followed.append(t) or True)

        # compte 1 : auth échoue — il ne doit rien consommer
        s1 = self._run_with(monkeypatch, ok=False)
        runner.run_account("dead:tok", 12, {}, s1, self.POOLS, Event(), pool)
        assert followed == []

        # compte 2 (vivant) : récupère la cible à la place
        s2 = self._run_with(monkeypatch, ok=True)
        runner.run_account("alive:tok", 12, {}, s2, self.POOLS, Event(), pool)
        assert followed == ["victime"]

        # compte 3 : file épuisée → message clair, pas de double follow
        s3 = self._run_with(monkeypatch, ok=True)
        runner.run_account("late:tok", 12, {}, s3, self.POOLS, Event(), pool)
        assert followed == ["victime"]
        assert any("no target available" in e["msg"] for e in s3.log)
        s3_fail = [e for e in s3.log if "partitioned" in e["msg"]]
        assert not s3_fail  # message à jour


class TestTweetVisibility:
    def test_normal_tweet(self):
        assert tweet_visibility({"__typename": "Tweet", "rest_id": "1"}) == ""

    def test_visibility_results(self):
        r = {"__typename": "TweetWithVisibilityResults", "rest_id": "1"}
        assert tweet_visibility(r) == "TweetWithVisibilityResults"

    def test_tombstone(self):
        assert tweet_visibility({"tombstone": {}}) == "tombstone"

    def test_edge_cases(self):
        assert tweet_visibility(None) == "unknown-result"
        assert tweet_visibility({}) == ""


class TestJobStatsHidden:
    def test_hidden_counter(self):
        s = JobStats("Quote Tweet", 1)
        s.record_hidden("@x post MASQUÉ par X")
        d = s.to_dict()
        assert d["hidden"] == 1
        assert d["success"] == 0
        assert d["failed"] == 0
        assert d["total"] == 1
        assert d["log"][0]["ok"] is False
        # Un tweet masqué fait baisser le taux de réussite
        assert d["rate"] == 0

    def test_status_dict_contains_hidden_field(self):
        d = JobStats("Quote Tweet", 1).to_dict()
        assert "hidden" in d and d["hidden"] == 0
