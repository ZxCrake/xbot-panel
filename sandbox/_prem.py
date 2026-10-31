import sys, os, json
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
for i,a in enumerate(accs):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            print(i, a["username"], "auth FAIL"); continue
        r = s._s.get("https://x.com/i/api/1.1/account/verify_credentials.json",
                     headers=s.headers("GET","/i/api/1.1/account/verify_credentials.json","https://x.com/home"))
        j = r.json()
        print(i, a["username"], "blue:", j.get("is_blue_verified"), "created:", j.get("created_at"))
    except Exception as e:
        print(i, a["username"], "ERR:", e)
