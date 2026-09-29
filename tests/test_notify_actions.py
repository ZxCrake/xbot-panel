"""Tests des actions de notification directe (12 Follow Target / 13 Send DM) :
- resolve_user_id : résolution @username → user_id (et check_premium refactoré)
- send_dm         : envoi de message privé
- runner.validate : fichiers requis pour les actions 12 et 13
"""
from unittest.mock import Mock

from xbot import runner
from xbot.x import actions


def _user_payload(**kwargs):
    return {"data": {"user": {"result": {"rest_id": "1234567", "legacy": {}, **kwargs}}}}


class TestResolveUserId:
    def test_happy_path(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = _user_payload()
        session.get.return_value = r
        uid, err = actions.resolve_user_id(session, "cible")
        assert uid == "1234567"
        assert err == ""

    def test_http_error(self):
        session = Mock()
        session.get.return_value = Mock(status_code=404)
        uid, err = actions.resolve_user_id(session, "cible")
        assert uid == ""
        assert "404" in err

    def test_missing_id(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = {"data": {"user": {"result": {"legacy": {}}}}}
        session.get.return_value = r
        uid, err = actions.resolve_user_id(session, "cible")
        assert uid == ""
        assert err != ""


class TestCheckPremium:
    def test_premium_flag_parsed(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = _user_payload(is_blue_verified=True)
        session.get.return_value = r
        info = actions.check_premium(session, "vip")
        assert info["ok"] is True and info["premium"] is True

    def test_not_premium(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = _user_payload()
        session.get.return_value = r
        info = actions.check_premium(session, "nobody")
        assert info["ok"] is True and info["premium"] is False


class TestSendDm:
    def test_success(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = {"event": {"type": "message_create"}}
        session.post_form.return_value = r
        assert actions.send_dm(session, "1234567", "hello") is True
        # le recipient_id est bien transmis tel quel
        data = session.post_form.call_args[0][1]
        assert data["recipient_id"] == "1234567"
        assert data["text"] == "hello"
        assert data["request_id"]  # uuid anti-doublon présent

    def test_error_payload_is_failure(self):
        session = Mock()
        r = Mock(status_code=200)
        r.json.return_value = {"errors": [{"message": "You cannot send messages to this user."}]}
        session.post_form.return_value = r
        assert actions.send_dm(session, "1234567", "hello") is False

    def test_http_error_is_failure(self):
        session = Mock()
        session.post_form.return_value = Mock(status_code=403)
        assert actions.send_dm(session, "1234567", "hello") is False


def _pools(**overrides):
    base = {
        "accounts": ["bot:token"],
        "all_usernames": ["bot"],
        "tweet_ids": [],
        "tweets": [],
        "replies": [],
        "users": [],
        "dms": [],
        "articles": [],
    }
    base.update(overrides)
    return base


class TestValidateNotifyActions:
    def test_follow_target_requires_users(self):
        assert runner.validate(12, {}, _pools()) == "No target specified"
        assert runner.validate(12, {}, _pools(users=["cible"])) == ""

    def test_send_dm_requires_users_and_dms(self):
        assert runner.validate(13, {}, _pools()) == "No target specified"
        assert runner.validate(13, {}, _pools(users=["cible"])) == "No DM text written"
        assert runner.validate(13, {}, _pools(users=["cible"], dms=[{"text": "hi"}])) == ""

    def test_actions_registered(self):
        assert runner.ACTION_NAMES[12] == "Follow Target"
        assert runner.ACTION_NAMES[13] == "Send DM"
        # cibles en file partagée (consommées une fois) + exécution unique par compte
        assert 12 in runner.TARGET_ACTIONS and 13 in runner.TARGET_ACTIONS
        assert 12 in runner.ONCE_ACTIONS and 13 in runner.ONCE_ACTIONS
