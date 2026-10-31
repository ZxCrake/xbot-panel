"""Test X accounts from their auth_token (read-only).

Connects through the same XSession pipeline as the bot (XCTID, XPFF, proxy),
then optionally looks up the profile and runs the read-only scrapers to verify
query IDs. Never prints the token, and never performs a write action.

Examples:
    python tools/test_account.py --workspace data/users/u-xxxxxxxx
    python tools/test_account.py --workspace data/users/u-xxxxxxxx --all
    python tools/test_account.py --workspace data/users/u-xxxxxxxx --index 1
    python tools/test_account.py --workspace data/users/u-xxxxxxxx --index 0 \
        --tweet 1561268905800175617 --scrape-tweet 1561268905800175617
    python tools/test_account.py --token <auth_token> --user <screen_name>
    python tools/test_account.py --workspace ... --index 0 --proxy user:pass@host:port
"""
import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from xbot import proxies as proxy_utils          # noqa: E402
from xbot import settings                        # noqa: E402
from xbot.x import actions, scraper              # noqa: E402
from xbot.x.session import XSession              # noqa: E402


def mask_proxy(proxy: str) -> str:
    if not proxy:
        return "(direct)"
    return re.sub(r"://[^@]+@", "://***@", proxy)


def read_accounts(path: str) -> list:
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                user = line.split(":")[0].lstrip("@")
                token = line.split(":")[-1]
                if user and token:
                    out.append((user, token))
    except OSError:
        pass
    return out


def load_config(workspace: str) -> dict:
    try:
        with open(os.path.join(workspace, "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def resolve_workspace(args) -> str:
    if args.workspace:
        return os.path.abspath(args.workspace)
    if args.accounts:
        return os.path.dirname(os.path.abspath(args.accounts))
    candidates = []
    try:
        names = sorted(os.listdir(settings.USER_DATA_ROOT))
    except OSError:
        names = []
    for name in names:
        directory = os.path.join(settings.USER_DATA_ROOT, name)
        if read_accounts(os.path.join(directory, "accounts.txt")):
            candidates.append(directory)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        sys.exit("No workspace with accounts found; pass --workspace or --token")
    sys.exit("Several workspaces found:\n  " + "\n  ".join(candidates)
             + "\nPass --workspace <dir>")


def verify_screen_name(session: XSession) -> str:
    """Best-effort screen_name for a bare token (calls account/verify_credentials)."""
    path = "/i/api/1.1/account/verify_credentials.json"
    try:
        r = session._request(
            "GET", "https://x.com" + path,
            headers=session.graphql_headers("GET", path, "https://x.com/home"),
            params={"include_entities": "false", "skip_status": "true"})
        if r.status_code == 200:
            return str(r.json().get("screen_name", "") or "")
    except Exception:
        pass
    return ""


def test_account(user: str, token: str, proxy: str,
                 tweet_id: str = "", scrape_tweet: str = "") -> bool:
    print(f"  proxy: {mask_proxy(proxy)}")
    with XSession(auth_token=token, proxy=proxy) as session:
        if not session.authenticate():
            reason = ("proxy/network error" if session.last_net_error
                      else "token invalide/expiré")
            print(f"  authenticate: ÉCHEC ({reason})")
            return False
        print("  authenticate: OK")

        if not user:
            user = verify_screen_name(session)
            if user:
                print(f"  compte: @{user}")

        if user:
            result, err = actions._lookup_user(session, user)
            if err:
                print(f"  profil: ÉCHEC ({err})")
            else:
                legacy = result.get("legacy", {}) or {}
                core = result.get("core", {}) or {}
                uid = result.get("rest_id") or result.get("id") or "?"
                premium = bool(result.get("is_blue_verified"))
                vtype = legacy.get("verified_type") or result.get("verified_type") or "-"
                name = legacy.get("name") or core.get("name") or ""
                print(f"  profil: id={uid} | premium={'oui' if premium else 'non'}"
                      f" | type={vtype} | nom={name}")
        else:
            print("  profil: ignoré (username inconnu — utilise --user)")

        if tweet_id:
            ok = actions.view_tweet(session, tweet_id)
            print(f"  TweetResultByRestId: {'OK' if ok else 'ÉCHEC'}")

        if scrape_tweet:
            for label, fn in (("Favoriters", scraper.favoriters),
                              ("Retweeters", scraper.retweeters),
                              ("TweetDetail", scraper.replies),
                              ("SearchTimeline", scraper.quotes)):
                try:
                    result = fn(session, scrape_tweet, max_results=5)
                    if result.get("error"):
                        print(f"  {label}: ÉCHEC ({result['error']})")
                    else:
                        print(f"  {label}: OK ({result.get('count', 0)} résultat(s))")
                except Exception as exc:
                    print(f"  {label}: EXC {type(exc).__name__}: {exc}")
        return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Test X accounts from their auth_token (read-only).")
    ap.add_argument("--workspace", help="user workspace dir (contains accounts.txt)")
    ap.add_argument("--accounts", help="path to an accounts.txt file")
    ap.add_argument("--index", type=int, default=0, help="account index (default 0)")
    ap.add_argument("--all", action="store_true", help="test every account")
    ap.add_argument("--token", help="auth_token directly (use with --user)")
    ap.add_argument("--user", help="screen_name for --token mode")
    ap.add_argument("--proxy", help="proxy override: user:pass@host:port")
    ap.add_argument("--no-proxy", action="store_true", help="force a direct connection")
    ap.add_argument("--tweet", default="", help="tweet ID for TweetResultByRestId")
    ap.add_argument("--scrape-tweet", default="",
                    help="tweet ID for Favoriters/Retweeters/TweetDetail/SearchTimeline")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between accounts in --all mode")
    args = ap.parse_args()

    if args.token:
        user = (args.user or "").lstrip("@")
        proxy = "" if args.no_proxy else (args.proxy or "")
        print(f"Compte: @{user or '?'}")
        ok = test_account(user, args.token.strip(), proxy,
                          args.tweet, args.scrape_tweet)
        return 0 if ok else 1

    workspace = resolve_workspace(args)
    accounts = read_accounts(os.path.join(workspace, "accounts.txt"))
    if not accounts:
        sys.exit(f"No accounts in {workspace}")
    cfg = load_config(workspace)

    if args.all:
        selected = list(enumerate(accounts))
    else:
        if not 0 <= args.index < len(accounts):
            sys.exit(f"--index {args.index} out of range (0..{len(accounts) - 1})")
        selected = [(args.index, accounts[args.index])]

    print(f"Workspace: {workspace}")
    print(f"Comptes: {len(accounts)} | mode proxy: {cfg.get('proxy_mode', 'static')}"
          f" | format: {cfg.get('proxy_session_format', 'auto')}")

    ok_count = 0
    for index, (user, token) in selected:
        if args.no_proxy:
            proxy = ""
        elif args.proxy:
            proxy = args.proxy
        else:
            proxy = proxy_utils.resolve_for_account(cfg, index)
        print(f"\nCompte {index}: @{user}")
        if test_account(user, token, proxy, args.tweet, args.scrape_tweet):
            ok_count += 1
        if len(selected) > 1:
            time.sleep(max(0.0, args.delay))

    if args.all:
        print(f"\nRésumé: {ok_count}/{len(selected)} compte(s) OK")
    return 0 if ok_count == len(selected) else 1


if __name__ == "__main__":
    sys.exit(main())
