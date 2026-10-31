import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts, BEARER_TOKEN
accs = load_accounts("sandbox/account.txt")
a = accs[0]
s = XSessionLite(a["auth_token"], ct0=a["ct0"])
s.authenticate()
h = s.headers("GET","/2/notifications/all","https://x.com/i/notifications")
for url in ("https://api.x.com/2/notifications/all",
            "https://x.com/i/api/2/notifications/all",
            "https://x.com/i/api/1.1/i/timeline.json"):
    r = s._s.get(url, headers=h)
    print(url, r.status_code, r.text[:200])
