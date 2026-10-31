import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import load_accounts
from curl_cffi import requests as cr
import re
accs = load_accounts("sandbox/account.txt")
for i in (0, 5):
    a = accs[i]
    s = cr.Session(impersonate="chrome124", timeout=20)
    r = s.get("https://x.com/home", headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "cookie": f"auth_token={a['auth_token']}",
    })
    txt = r.text
    m = re.findall(r'/s-ondemand/[\w.]+', txt)
    print(i, "ondemand:", m)
    # also print number of <script>
    print(i, "scripts:", txt.count("<script"))
    print(i, "len:", len(txt))
    print(i, "tail:", txt[-800:])
    s.close()
