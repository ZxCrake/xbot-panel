import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")

def js(label, body):
    url = "https://x.com/i/api/1.1/dm/new2.json"
    r = s._s.post(url, headers=s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"), json=body)
    print(label, r.status_code, r.text[:400])

# try dotted numeric request_id
def dotted():
    return f"{time.time():.4f}"

js("E dotted reqid:", {
    "request_id": dotted(),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"E","entities":{"user_mentions":[],"urls":[],"hashtags":[]}},
        "sender_id": "2232650113",
        "recipient_id": uid,
        "created_timestamp": int(time.time()*1000),
    }
})
# with "type": "message_create" lowercase
js("F lowercase:", {
    "request_id": dotted(),
    "event": {
        "type": "message_create",
        "message_data": {"text":"F","entities":{"user_mentions":[],"urls":[],"hashtags":[]}},
        "sender_id": "2232650113",
        "recipient_id": uid,
        "created_timestamp": int(time.time()*1000),
    }
})
# minimal
js("G minimal:", {
    "request_id": dotted(),
    "event": {
        "type": "message_create",
        "message_data": {"text":"G"},
        "recipient_id": uid,
    }
})
