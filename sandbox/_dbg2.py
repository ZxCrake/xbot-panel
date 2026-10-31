import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from sandbox.post_tweet import load_accounts
from curl_cffi import requests as cr
import re
accs = load_accounts("sandbox/account.txt")
for i in (0, 4, 5, 6, 7, 8, 9):
    a = accs[i]
    s = cr.Session(impersonate="chrome124", timeout=20)
    r = s.get("https://x.com/home", headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "cookie": f"auth_token={a['auth_token']}",
    })
    txt = r.text
    print("===", i, a["username"], "len", len(txt))
    # find ondemand pattern
    for m in re.finditer(r'/s-ondemand/[\w.]+', txt):
        print(" od:", m.group(0))
    # first 300 chars
    print("  ", txt[:300])
    s.close()
