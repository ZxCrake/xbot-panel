import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
sender_id = "2232650113"

def form(path, data):
    h = s.headers("POST", path, "https://x.com/home")
    h["content-type"] = "application/x-www-form-urlencoded"
    return s._s.post("https://x.com"+path, headers=h, data=data)

def js(path, body):
    return s._s.post("https://x.com"+path, headers=s.headers("POST",path,"https://x.com/home"), json=body)

r = form("/i/api/1.1/dm/init.json", {
    "request_id": str(uuid.uuid4()),
    "participant": uid,
})
print("init:", r.status_code, r.text[:400])
try:
    j = r.json()
    conv = j.get("conversation",{}).get("id") or j.get("conversation_id") or ""
except Exception:
    conv = ""
print("conversation:", conv)

if conv:
    body = {
        "request_id": str(uuid.uuid4()),
        "event": {
            "type": "MessageCreate",
            "conversation_id": conv,
            "message_data": {"text": str(int(time.time())), "entities": {"user_mentions": [], "urls": [], "hashtags": []}},
            "sender_id": sender_id,
            "created_timestamp": int(time.time()*1000),
        }
    }
    r = js("/i/api/1.1/dm/new2.json", body)
    print("new2:", r.status_code, r.text[:600])
