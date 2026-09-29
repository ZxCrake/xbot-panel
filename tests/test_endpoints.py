from .conftest import auth_headers


def test_health(client):
    assert client.get("/health").get_json()["ok"] is True


def test_admin_gating(client, admin_user, normal_user):
    h_admin = auth_headers(client, *admin_user)
    h_user = auth_headers(client, *normal_user)
    assert client.get("/api/admin/users", headers=h_admin).status_code == 200
    assert client.get("/api/admin/users", headers=h_user).status_code == 403


def test_admin_create_and_delete_user(client, admin_user):
    h = auth_headers(client, *admin_user)
    r = client.post("/api/admin/users", headers=h,
                    json={"username": "tmpuser", "password": "supersecret1"})
    assert r.get_json() == {"ok": True}
    users = client.get("/api/admin/users", headers=h).get_json()["users"]
    assert any(u["username"] == "tmpuser" for u in users)
    assert client.delete("/api/admin/users/tmpuser", headers=h).get_json() == {"ok": True}


def test_admin_cannot_delete_self(client, admin_user):
    h = auth_headers(client, *admin_user)
    r = client.delete("/api/admin/users/boss", headers=h)
    assert r.status_code == 400


def test_file_whitelist_and_roundtrip(client, normal_user):
    h = auth_headers(client, *normal_user)
    assert client.get("/api/file/evil.txt", headers=h).status_code == 400
    client.post("/api/file/accounts.txt", headers=h, json={"content": "a:b:c"})
    assert client.get("/api/file/accounts.txt", headers=h).get_json()["content"] == "a:b:c"


def test_config_validation_rejects_bad_values(client, normal_user):
    h = auth_headers(client, *normal_user)
    assert client.post("/api/config", headers=h, json={"threads": 99999}).status_code == 400
    assert client.post("/api/config", headers=h, json={"threads": "abc"}).status_code == 400
    assert client.post("/api/config", headers=h, json={"threads": 10}).status_code == 200


def test_run_rejects_invalid_action(client, normal_user):
    h = auth_headers(client, *normal_user)
    assert client.post("/api/run", headers=h, json={"action_mode": 999}).status_code == 400


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers
