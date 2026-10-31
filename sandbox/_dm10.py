import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")

def form(url, data):
    path = url.split("x.com",1)[-1]
    h = s.headers("POST", path, "https://x.com/home")
    h["content-type"] = "application/x-www-form-urlencoded"
    return s._s.post(url, headers=h, data=data)

def jsn(url, body):
    path = url.split("x.com",1)[-1]
    return s._s.post(url, headers=s.headers("POST", path, "https://x.com/home"), json=body)

# api.x.com form
r = form("https://api.x.com/1.1/dm/new2.json", {
    "request_id": str(uuid.uuid4()),
    "recipient_id": uid,
    "text": "api-form",
})
print("api-form:", r.status_code, r.text[:300])

# api.x.com json
r = jsn("https://api.x.com/1.1/dm/new2.json", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"api-json","entities":{}},
        "recipient_id": uid,
    }
})
print("api-json:", r.status_code, r.text[:300])

# plain new.json
r = form("https://api.x.com/1.1/dm/new.json", {
    "request_id": str(uuid.uuid4()),
    "recipient_id": uid,
    "text": "new",
})
print("new:", r.status_code, r.text[:300])
