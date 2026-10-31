import os
import tempfile

import pytest

# Configure a throwaway environment BEFORE importing the app.
_tmpdir = tempfile.mkdtemp(prefix="xbot-test-")
os.environ["XBOT_ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"
os.environ["DATA_ROOT"] = _tmpdir
os.environ["LOG_DIR"] = os.path.join(_tmpdir, "logs")
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["BEHIND_PROXY"] = "false"
os.environ["LOGIN_MAX_ATTEMPTS"] = "3"
os.environ["XBOT_QUERY_IDS_AUTOREFRESH"] = "0"  # no network in tests

from xbot import create_app           # noqa: E402
from xbot.db import create_all        # noqa: E402
from xbot import auth                 # noqa: E402
from xbot.security import limiter     # noqa: E402


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch):
    from curl_cffi import requests as curl_requests
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in tests")
    monkeypatch.setattr(curl_requests.Session, "request", blocked)


@pytest.fixture(scope="session")
def app():
    application = create_app()
    limiter.enabled = False  # don't trip rate limits during tests
    create_all()
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    with app.app_context():
        if not auth.get_user("boss"):
            auth.create_user("boss", "supersecret1", role="admin")
    return ("boss", "supersecret1")


@pytest.fixture()
def normal_user(app):
    with app.app_context():
        if not auth.get_user("alice"):
            auth.create_user("alice", "supersecret1", role="user")
    return ("alice", "supersecret1")


def token_for(client, username, password):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["token"]


def auth_headers(client, username, password):
    return {"Authorization": "Bearer " + token_for(client, username, password)}
