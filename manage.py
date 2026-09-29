"""Admin CLI — user management.

Usage:
    python manage.py init                         # create tables (SQLite/dev)
    python manage.py upgrade                      # migrate existing database
    python manage.py add <username> [password] [role]   # role: user|moderator|admin
    python manage.py passwd <username> [password]
    python manage.py role <username> <role>
    python manage.py del <username>
    python manage.py list

Password is prompted (hidden) if omitted.
"""
import sys
import getpass

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from xbot.db import init_engine, upgrade_schema, session, User
from xbot import auth


def _ask_password() -> str:
    p1 = getpass.getpass("Password: ")
    p2 = getpass.getpass("Confirm: ")
    if p1 != p2:
        print("❌ Passwords do not match")
        sys.exit(1)
    return p1


def main():
    init_engine()
    upgrade_schema()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]

    if cmd in ("init", "upgrade"):
        print("✅ Database tables ready")
        return

    if cmd == "list":
        users = auth.list_users()
        if not users:
            print("No users.")
        for u in users:
            print(f"- {u.username}  [{u.role}]" + ("" if u.is_active else "  (inactive)"))
        return

    if cmd in ("add", "passwd", "del", "role") and len(sys.argv) < 3:
        print("❌ username required")
        sys.exit(1)

    if cmd == "add":
        username = sys.argv[2]
        role = sys.argv[4] if len(sys.argv) > 4 else "user"
        password = sys.argv[3] if len(sys.argv) > 3 else _ask_password()
        try:
            auth.create_user(username, password, role=role)
            print(f"✅ User created: {username} [{role}]")
        except ValueError as e:
            print(f"❌ {e}"); sys.exit(1)

    elif cmd == "passwd":
        username = sys.argv[2]
        password = sys.argv[3] if len(sys.argv) > 3 else _ask_password()
        try:
            print(f"✅ Password updated: {username}" if auth.set_password(username, password)
                  else f"❌ User not found: {username}")
        except ValueError as e:
            print(f"❌ {e}"); sys.exit(1)

    elif cmd == "role":
        username, role = sys.argv[2].strip().lower(), sys.argv[3]
        if role not in auth.ROLE_RANK:
            print("❌ role must be one of: user, moderator, admin"); sys.exit(1)
        u = auth.get_user(username)
        if not u:
            print(f"❌ User not found: {username}"); sys.exit(1)
        u.role = role; u.token_version += 1
        session().commit()
        print(f"✅ {username} is now [{role}]")

    elif cmd == "del":
        username = sys.argv[2]
        print(f"✅ User deleted: {username}" if auth.delete_user(username)
              else f"❌ User not found: {username}")
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
