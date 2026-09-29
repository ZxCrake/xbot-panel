import io
import os
import uuid
from pathlib import Path
from threading import Event, BoundedSemaphore
from unittest.mock import Mock

import pytest
from flask import g

from xbot import auth, settings, context, runner
from xbot.files import profile_path, safe_file
from xbot.security import validate_config
from xbot.x import actions
from xbot.x.session import XSession
from .conftest import auth_headers


@pytest.fixture
def member(app, client):
    name = "test_" + uuid.uuid4().hex[:12]
    with app.app_context():
        auth.create_user(name, "strong-password", "user")
    return name, auth_headers(client, name, "strong-password")


def test_recreation_does_not_restore_sessions_or_files(app, client, member, admin_user):
    name, old_headers = member
    admin = auth_headers(client, *admin_user)
    assert client.post("/api/file/accounts.txt", headers=old_headers,
                       json={"content": "old-account:synthetic-secret"}).status_code == 200
    with app.app_context():
        old_key = auth.get_user(name).workspace_key
        old_dir = auth.user_dir(name)
        old_runner = runner.BotRunner()
        context.runners[old_key] = old_runner
    assert client.delete(f"/api/admin/users/{name}", headers=admin).status_code == 200
    assert old_runner.stop_event.is_set()
    assert old_runner.start(3, {}, old_dir) == "User access has been revoked"
    assert client.get("/api/me", headers=old_headers).status_code == 401
    assert client.post("/api/admin/users", headers=admin,
                       json={"username": name, "password": "strong-password"}).status_code == 200
    fresh = auth_headers(client, name, "strong-password")
    assert client.get("/api/me", headers=old_headers).status_code == 401
    assert client.get("/api/file/accounts.txt", headers=fresh).json == {"content": ""}
    with app.app_context():
        assert auth.user_dir(name) != old_dir
    assert Path(old_dir, "accounts.txt").read_text() == "old-account:synthetic-secret"
    # A request carrying the old identity cannot create a replacement runner.
    with app.test_request_context():
        g.user, g.workspace_key = name, old_key
        from werkzeug.exceptions import Unauthorized
        with pytest.raises(Unauthorized):
            context.get_runner()


def test_legacy_tokens_are_rejected(app, client, member):
    name, _ = member
    with app.app_context():
        token = auth._serializer().dumps({"u": name, "v": 1})
    assert client.get("/api/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_moderator_cannot_read_account_secrets(app, client, member):
    name, _ = member
    mod = "mod_" + uuid.uuid4().hex[:12]
    with app.app_context():
        auth.create_user(mod, "strong-password", "moderator")
    headers = auth_headers(client, mod, "strong-password")
    assert client.get("/api/admin/users", headers=headers).status_code == 200
    assert client.get(f"/api/admin/users/{name}/detail", headers=headers).status_code == 403


def test_user_cannot_access_other_workspace(client, member, normal_user):
    _, headers = member
    other = auth_headers(client, *normal_user)
    client.post("/api/file/accounts.txt", headers=headers, json={"content": "isolated:secret"})
    assert "isolated:secret" not in client.get("/api/file/accounts.txt", headers=other).json["content"]


@pytest.mark.parametrize("name", ["../pfp.jpg", "..\\pfp.jpg", "/tmp/a.jpg", "C:\\temp\\a.jpg",
                                   "C:pfp.jpg", "file.txt", "a.jpg:secret", "pfp.jpg/../x.jpg"])
def test_profile_paths_rejected(client, member, name):
    _, headers = member
    assert client.post("/api/config", headers=headers, json={"pfp_image": name}).status_code == 400


def test_profile_worker_uses_user_directory(tmp_path, monkeypatch):
    (tmp_path / "pfp.jpg").write_bytes(b"synthetic-image")
    pools = {"accounts": ["demo:fake"], "tweet_ids": []}
    cfg = {"pfp_image": "pfp.jpg", "limit": 1}
    assert runner.validate(8, cfg, pools, str(tmp_path)) == ""
    session = Mock()
    session.authenticate.return_value = True
    update = Mock(return_value=True)
    monkeypatch.setattr(actions, "update_profile_picture", update)
    runner._run_session(session, "demo", 8, cfg, runner.JobStats("PFP", 1), pools, Event())
    update.assert_called_once_with(session, str(tmp_path / "pfp.jpg"))


def test_absolute_profile_path_cannot_bypass_runner_validation(tmp_path):
    image = tmp_path / "outside.jpg"
    image.write_bytes(b"synthetic")
    assert runner.validate(8, {"pfp_image": str(image)}, {"accounts": ["demo:fake"]}, str(tmp_path))


def test_file_symlink_cannot_escape(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic")
    user = tmp_path / "user"
    user.mkdir()
    try:
        (user / "accounts.txt").symlink_to(outside)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    with pytest.raises(ValueError):
        safe_file(str(user), "accounts.txt")


def test_upload_obeys_its_own_size_limit(client, member, monkeypatch):
    _, headers = member
    monkeypatch.setattr(settings, "MAX_PFP_BYTES", 8)
    result = client.post("/api/upload-pfp", headers=headers,
                         data={"file": (io.BytesIO(b"a" * 9), "pfp.jpg")})
    assert result.status_code == 413


@pytest.mark.parametrize("body", [[1], "bad", 42, None])
def test_non_object_json_is_bad_request(client, body):
    import json
    assert client.post("/api/login", data=json.dumps(body), content_type="application/json").status_code == 400


def test_missing_scraper_configuration_makes_no_request(client, member, monkeypatch):
    _, headers = member
    # Simulate the X integration being version-mismatched (queryIds unknown)
    from xbot.x import constants
    monkeypatch.setattr(constants, "FAVORITERS_QUERYID", "")
    monkeypatch.setattr(constants, "RETWEETERS_QUERYID", "")
    monkeypatch.setattr(constants, "TWEET_DETAIL_QUERYID", "")
    monkeypatch.setattr(constants, "SEARCH_TIMELINE_QUERYID", "")
    assert client.post("/api/scrape", headers=headers,
                       json={"tweet_id": "123", "targets": ["likes"]}).status_code == 503


@pytest.mark.parametrize("body", [{"errors": [{"message": "failed"}]}, {}, {"data": None},
                                   {"data": {"favorite_tweet": None}}, []])
def test_http_200_errors_are_not_success(body):
    response = Mock(status_code=200)
    response.json.return_value = body
    session = Mock()
    session.post.return_value = response
    assert actions.like(session, "123") is False


def test_valid_graphql_response_is_success():
    response = Mock(status_code=200)
    response.json.return_value = {"data": {"favorite_tweet": "Done"}}
    assert actions.response_ok(response, graphql=True)


def test_account_progress_updates_on_failure(monkeypatch):
    def failed(*args):
        raise RuntimeError("synthetic")
    monkeypatch.setattr(runner, "_run_account", failed)
    stats = runner.JobStats("test", 1)
    with pytest.raises(RuntimeError):
        runner.run_account("demo:fake", 3, {}, stats, {}, Event())
    assert stats.accounts_done == 1


def test_stop_interrupts_delay_and_releases_capacity(tmp_path, monkeypatch):
    (tmp_path / "accounts.txt").write_text("demo:fake\nother:fake")
    (tmp_path / "tweet_ids.txt").write_text("123")
    started = Event()
    calls = []
    def work(acc, action, cfg, stats, pools, stop):
        calls.append(acc)
        started.set()
        runner._sleep_between({"delay_min": 3600, "delay_max": 3600}, stop)
    monkeypatch.setattr(runner, "_run_account", work)
    semaphore = BoundedSemaphore(1)
    monkeypatch.setattr(runner, "JOB_SLOTS", semaphore)
    first, second = runner.BotRunner(), runner.BotRunner()
    assert first.start(3, {"threads": 1}, str(tmp_path)) == ""
    try:
        assert started.wait(2)
        assert "capacity" in second.start(3, {}, str(tmp_path))
    finally:
        first.stop()
        first._thread.join(2)
    assert not first.is_running()
    assert len(calls) == 1
    assert semaphore.acquire(blocking=False)
    semaphore.release()


def test_thread_and_account_limits_are_enforced(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        validate_config({"threads": settings.MAX_THREADS_PER_USER + 1})
    monkeypatch.setattr(settings, "MAX_ACCOUNTS_PER_JOB", 1)
    assert "At most" in runner.validate(3, {}, {"accounts": ["a:x", "b:y"]}, str(tmp_path))


def test_stopped_session_does_not_send_request():
    stop = Event()
    with XSession("synthetic", stop_event=stop) as session:
        stop.set()
        with pytest.raises(RuntimeError, match="Job stopped"):
            session._request("GET", "https://x.com")


def test_external_revocation_interrupts_long_wait():
    from threading import Thread
    active = Event()
    active.set()
    stop = runner.AccessEvent(active.is_set)
    finished = Event()
    thread = Thread(target=lambda: (stop.wait(3600), finished.set()), daemon=True)
    thread.start()
    active.clear()
    try:
        assert finished.wait(2)
        assert stop.is_set()
    finally:
        stop.set()
        thread.join(2)


def test_pages_use_external_scripts_and_strict_csp(client):
    for path in ("/", "/login", "/admin", "/admin/login"):
        result = client.get(path)
        assert b"<script>" not in result.data
        assert "script-src 'self';" in result.headers["Content-Security-Policy"]
    assert client.get("/static/safe-dom.js").status_code == 200
