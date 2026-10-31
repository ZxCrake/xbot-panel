import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")

def js(label, url, body):
    path = url.split("x.com",1)[-1]
    r = s._s.post(url, headers=s.headers("POST", path, f"https://x.com/messages/{uid}"), json=body)
    print(label, r.status_code, r.text[:400])

body = {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"X","entities":{}},
        "sender_id": "2232650113",
        "recipient_id": uid,
        "created_timestamp": int(time.time()*1000),
    }
}
js("api.x.com:", "https://api.x.com/i/api/1.1/dm/new2.json", body)
js("x.com:",       "https://x.com/i/api/1.1/dm/new2.json", body)

# form encoded
def fm(label, url, data):
    path = url.split("x.com",1)[-1]
    h = s.headers("POST", path, f"https://x.com/messages/{uid}")
    h["content-type"] = "application/x-www-form-urlencoded"
    r = s._s.post(url, headers=h, data=data)
    print(label, r.status_code, r.text[:400])

data = {
    "request_id": str(uuid.uuid4()),
    "recipient_id": uid,
    "text": "Y",
    "cards_platform": "Web-12",
    "include_cards": "0",
    "include_quote_count": "false",
    "dm_users": "false",
}
fm("form x.com:", "https://x.com/i/api/1.1/dm/new2.json", data)
fm("form api.x.com:", "https://api.x.com/i/api/1.1/dm/new2.json", data)
