"""Open a real browser logged into an X account from its auth_token cookie.

Usage:
    python login_with_token.py <auth_token>
    python login_with_token.py <auth_token> --proxy user:pass@host:port
    python login_with_token.py                # prompts for the token

The token is injected as the `auth_token` cookie for x.com; X then treats the
session as logged in. Use to verify a token is still valid, or to manage the
account by hand. Requires:  pip install playwright  &&  playwright install chromium
"""
import sys
import argparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright missing. Run:  pip install playwright && playwright install chromium")


def parse_proxy(raw: str):
    """Turn 'user:pass@host:port' (or 'host:port') into a Playwright proxy dict."""
    if not raw:
        return None
    creds = None
    if "@" in raw:
        creds, raw = raw.rsplit("@", 1)
    server = raw if raw.startswith("http") else f"http://{raw}"
    proxy = {"server": server}
    if creds and ":" in creds:
        user, pwd = creds.split(":", 1)
        proxy["username"], proxy["password"] = user, pwd
    return proxy


def cookies_for(token: str):
    return [
        {"name": "auth_token", "value": token, "domain": d, "path": "/",
         "httpOnly": True, "secure": True}
        for d in (".x.com", ".twitter.com")
    ]


def main():
    ap = argparse.ArgumentParser(description="Log into X with an auth_token in a browser.")
    ap.add_argument("auth_token", nargs="?", help="the account's auth_token cookie")
    ap.add_argument("--proxy", help="user:pass@host:port (match the account's usual IP)")
    ap.add_argument("--headless", action="store_true", help="run without a visible window")
    ap.add_argument("--url", default="https://x.com/home", help="page to open after login")
    args = ap.parse_args()

    token = (args.auth_token or input("auth_token: ")).strip()
    if not token:
        sys.exit("No auth_token provided.")

    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")

    with sync_playwright() as p:
        launch = {"headless": args.headless}
        proxy = parse_proxy(args.proxy)
        if proxy:
            launch["proxy"] = proxy
        browser = p.chromium.launch(**launch)
        ctx = browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})
        ctx.add_cookies(cookies_for(token))
        page = ctx.new_page()
        print(f"Opening {args.url} …")
        page.goto(args.url, wait_until="domcontentloaded")

        # Quick validity hint: logged-out X redirects to /login or /i/flow/login
        cur = page.url
        if "/login" in cur or "/flow/login" in cur:
            print("⚠️  Looks logged OUT — token likely invalid/expired (url:", cur, ")")
        else:
            print("✅ Logged in (url:", cur, ")")

        if args.headless:
            print("Headless mode — closing.")
        else:
            input("Browser open. Press Enter here to close…")
        browser.close()


if __name__ == "__main__":
    main()
