import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
# who am I? use me.json
r = s._s.get("https://x.com/i/api/1.1/account/settings.json",
    headers=s.headers("GET","/i/api/1.1/account/settings.json","https://x.com/home"))
print("settings:", r.status_code, r.text[:200])
# try verify
r = s._s.get("https://x.com/i/api/1.1/account/verify_credentials.json",
    headers=s.headers("GET","/i/api/1.1/account/verify_credentials.json","https://x.com/home"))
print("verify:", r.status_code, r.text[:400])
