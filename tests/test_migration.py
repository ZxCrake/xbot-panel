import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_original_unversioned_database_is_preserved(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "legacy.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(database),
           "DATA_ROOT": str(tmp_path), "LOG_DIR": str(tmp_path / "logs")}
    def run(*args):
        result = subprocess.run([sys.executable, *args], cwd=root, env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
    run("-m", "alembic", "upgrade", "0001")
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE alembic_version")
        db.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                   ("legacy", "synthetic-hash", "admin", "2026-01-01 00:00:00"))
    user_dir = tmp_path / "users" / "legacy"
    user_dir.mkdir(parents=True)
    (user_dir / "accounts.txt").write_text("synthetic-account:synthetic-token")
    run("manage.py", "upgrade")
    run("manage.py", "upgrade")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT username, workspace_key, password_hash FROM users").fetchall() == [
            ("legacy", "legacy", "synthetic-hash")]
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0002",)
    assert (user_dir / "accounts.txt").read_text() == "synthetic-account:synthetic-token"
    assert len(list(tmp_path.glob("legacy.db.before-workspaces-*.bak"))) == 1
