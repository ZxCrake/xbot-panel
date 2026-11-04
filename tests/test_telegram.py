"""Tests du bot Telegram — aucun accès réseau (client factice)."""
import json

import pytest

from xbot import telegram_bot as tb
from xbot.runner import ACTION_NAMES


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, method, **payload):
        self.calls.append((method, payload))
        if method == "getUpdates":
            return []
        return {"message_id": 1}


def make_bot(tmp_path, pinned=None, admin="Nx0xb"):
    store = tb.AdminStore(str(tmp_path / "telegram.json"))
    return tb.TelegramBot(FakeClient(), admin, store, pinned_id=pinned)


class TestAuthorization:
    def test_username_before_pinning(self):
        assert tb.is_authorized(1, "Nx0xb", None, "Nx0xb") is True
        assert tb.is_authorized(1, "nx0xb", None, "Nx0xb") is True
        assert tb.is_authorized(1, "@Nx0xb", None, "Nx0xb") is True
        assert tb.is_authorized(1, "autre", None, "Nx0xb") is False
        assert tb.is_authorized(1, "", None, "Nx0xb") is False

    def test_pinned_id_wins_over_username(self):
        # Un usurpateur qui prend le @username ne passe plus.
        assert tb.is_authorized(42, "Nx0xb", 42, "Nx0xb") is True
        assert tb.is_authorized(99, "Nx0xb", 42, "Nx0xb") is False

    def test_first_contact_pins_id(self, tmp_path):
        bot = make_bot(tmp_path)
        assert bot._allow({"id": 4242, "username": "Nx0xb"}) is True
        assert bot.admin_id == 4242
        saved = json.loads((tmp_path / "telegram.json").read_text())
        assert saved["admin_id"] == 4242

    def test_after_pin_other_accounts_are_refused(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)
        assert bot._allow({"id": 7, "username": "Nx0xb"}) is False
        assert bot._allow({"id": 7, "username": "quelqu_un"}) is False


class TestStore:
    def test_roundtrip(self, tmp_path):
        store = tb.AdminStore(str(tmp_path / "sub" / "t.json"))
        assert store.load() == {}
        store.save({"admin_id": 5})
        assert store.load() == {"admin_id": 5}

    def test_corrupt_file_is_ignored(self, tmp_path):
        p = tmp_path / "t.json"
        p.write_text("{pas du json")
        assert tb.AdminStore(str(p)).load() == {}


class TestMenus:
    def test_main_menu_has_every_section(self):
        kb = tb.main_menu_keyboard()["inline_keyboard"]
        data = [btn["callback_data"] for row in kb for btn in row]
        for expected in ("v:dash", "v:users", "v:run", "v:farm", "v:login", "v:server"):
            assert expected in data

    def test_callback_data_fits_telegram_limit(self):
        kb = tb.actions_keyboard("un_nom_dutilisateur_tres_long_32c")["inline_keyboard"]
        for row in kb:
            for btn in row:
                assert len(btn["callback_data"].encode()) <= 64

    def test_actions_keyboard_lists_all_actions(self):
        kb = tb.actions_keyboard("alice")["inline_keyboard"]
        labels = [btn["text"] for row in kb for btn in row]
        for num in ACTION_NAMES:
            assert any(t.startswith(f"{num}.") for t in labels)

    def test_confirm_text_names_the_action(self):
        text = tb.confirm_text("alice", 14)
        assert "Change Email" in text and "alice" in text

    def test_esc_blocks_html_injection(self):
        assert "<b>" not in tb.esc("<b>x</b>")
        assert "&lt;b&gt;" in tb.esc("<b>x</b>")


class TestDispatch:
    def test_unauthorized_message_gets_refusal(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)
        bot._handle({"message": {"chat": {"id": 7}, "from": {"id": 7, "username": "x"},
                                 "text": "/start"}})
        method, payload = bot.client.calls[-1]
        assert method == "sendMessage" and "pas ouvert" in payload["text"].lower()

    def test_authorized_message_shows_menu(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)
        bot._handle({"message": {"chat": {"id": 4242},
                                 "from": {"id": 4242, "username": "Nx0xb"},
                                 "text": "/start"}})
        method, payload = bot.client.calls[-1]
        assert method == "sendMessage"
        assert "inline_keyboard" in payload["reply_markup"]

    def test_stranger_callback_is_answered_with_refusal(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)
        bot._handle({"callback_query": {"id": "1", "from": {"id": 7},
                                        "data": "v:dash"}})
        method, payload = bot.client.calls[-1]
        assert method == "answerCallbackQuery" and payload.get("show_alert") is True

    def test_long_text_is_truncated(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)
        bot._send_text(1, "x" * (tb.MAX_TEXT + 500))
        assert len(bot.client.calls[-1][1]["text"]) <= tb.MAX_TEXT + 1


class TestScreens:
    def test_dashboard_counts_users(self, app, admin_user):
        with app.app_context():
            text = tb.dashboard_text()
        assert "Tableau de bord" in text and "Utilisateurs" in text

    def test_logins_screen_lists_audit_rows(self, app, admin_user):
        from xbot.db import session, AuditLog
        with app.app_context():
            s = session()
            s.add(AuditLog(action="login.ok", username="admin", detail=None, ip="10.0.0.1"))
            s.commit()
            text = tb.logins_text()
        assert "connexions" in text.lower() and "10.0.0.1" in text

    def test_login_notification_contains_user_and_time(self, tmp_path):
        bot = make_bot(tmp_path, pinned=4242)

        class Row:
            action = "login.ok"
            username = "admin"
            detail = None
            ip = "1.2.3.4"
            ts = None

        bot._notify_login(Row())
        method, payload = bot.client.calls[-1]
        assert method == "sendMessage" and "admin" in payload["text"]
        assert "1.2.3.4" in payload["text"]


class TestNoNetworkAtImport:
    def test_disabled_without_token(self, monkeypatch):
        monkeypatch.setattr(tb.settings, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(tb, "_singleton", None)
        assert tb.start_from_settings() is None
