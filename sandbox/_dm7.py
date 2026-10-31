import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
sender_id = 2232650113
uid_int = int(uid)

def js(label, body):
    r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
        headers=s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"),
        json=body)
    print(label, r.status_code, r.text[:400])

# Int sender_id/recipient_id
js("A:", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"A","entities":{"user_mentions":[],"urls":[],"hashtags":[]}},
        "sender_id": sender_id,
        "recipient_id": uid_int,
        "created_timestamp": int(time.time()*1000),
    },
})
# With `additional_owners`?
js("B:", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"B","entities":{}},
        "sender_id": str(sender_id),
        "recipient_id": str(uid_int),
    },
})
# Just event, string types
js("C:", {
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"C","entities":{}},
        "sender_id": str(sender_id),
        "recipient_id": str(uid_int),
    },
    "request_id": str(uuid.uuid4()),
})
# no sender_id
js("D:", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text":"D","entities":{}},
        "recipient_id": str(uid_int),
        "created_timestamp": int(time.time()*1000),
    },
})
