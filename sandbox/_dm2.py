import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
sender_id = "2232650113"
stamp = str(int(time.time()))

ev = {
    "type": "MessageCreate",
    "message_data": {"text": stamp, "entities": {}},
    "sender_id": sender_id,
    "recipient_id": uid,
    "created_timestamp": int(time.time()*1000),
}
body = {"request_id": str(uuid.uuid4()), "event": ev}

# json
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
    headers={**s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}")},
    json=body)
print("json+sender:", r.status_code, r.text[:300])
