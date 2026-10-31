import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
stamp = str(int(time.time()))
h = s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}")
h["content-type"] = "application/x-www-form-urlencoded"
data = {
    "request_id": str(uuid.uuid4()),
    "recipient_id": uid,
    "text": stamp,
    "cards_platform": "Web-12",
    "include_cards": "0",
    "include_quote_count": "false",
    "dm_users": "false",
}
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json", headers=h, data=data)
print("form:", r.status_code, r.text[:400])
