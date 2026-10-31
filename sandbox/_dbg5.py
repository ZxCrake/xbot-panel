import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import load_accounts
from x_client_transaction.constants import ON_DEMAND_FILE_REGEX, ON_DEMAND_HASH_PATTERN
from curl_cffi import requests as cr

accs = load_accounts("sandbox/account.txt")
for i in (0, 1, 2, 3, 5, 6, 7, 8, 9):
    a = accs[i]
    s = cr.Session(impersonate="chrome124", timeout=20)
    r = s.get("https://x.com/home", headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "cookie": f"auth_token={a['auth_token']}",
    })
    m = ON_DEMAND_FILE_REGEX.search(r.text)
    print(i, a["username"], "od match:", m.group(1) if m else "None")
    s.close()
