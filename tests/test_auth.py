from xbot import auth
from .conftest import auth_headers


def test_password_is_argon2_hashed(app, normal_user):
    with app.app_context():
        u = auth.get_user("alice")
        assert u.password_hash.startswith("$argon2")
        assert "supersecret1" not in u.password_hash


def test_login_success_and_me(client, normal_user):
    u, p = normal_user
    r = client.post("/api/login", json={"username": u, "password": p})
    assert r.status_code == 200
    body = r.get_json()
    assert body["role"] == "user" and body["is_admin"] is False
    me = client.get("/api/me", headers={"Authorization": "Bearer " + body["token"]})
    assert me.get_json()["username"] == "alice"


def test_login_wrong_password(client, normal_user):
    r = client.post("/api/login", json={"username": "alice", "password": "WRONG"})
    assert r.status_code == 401


def test_no_token_is_unauthorized(client):
    assert client.get("/api/me").status_code == 401


def test_bad_token_is_unauthorized(client):
    assert client.get("/api/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_brute_force_lockout(client, app):
    with app.app_context():
        auth.create_user("victim", "supersecret1", role="user")
    for _ in range(3):  # LOGIN_MAX_ATTEMPTS=3 in tests
        client.post("/api/login", json={"username": "victim", "password": "nope"})
    # Now even the correct password is rejected while locked.
    r = client.post("/api/login", json={"username": "victim", "password": "supersecret1"})
    assert r.status_code == 401


def test_password_change_revokes_tokens(client, app):
    with app.app_context():
        auth.create_user("rev", "supersecret1", role="user")
    h = auth_headers(client, "rev", "supersecret1")
    assert client.get("/api/me", headers=h).status_code == 200
    with app.app_context():
        auth.set_password("rev", "newsecret123")
    # Old token no longer valid (token_version bumped).
    assert client.get("/api/me", headers=h).status_code == 401
