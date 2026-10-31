import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
sender_id = "2232650113"

def T(label, body):
    r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
        headers=s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"),
        json=body)
    print(label, r.status_code, r.text[:400])

# Try: request_id + event all inside a single nested structure?
T("v4:", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {
            "text": "v4",
            "entities": {"user_mentions":[], "urls":[], "hashtags":[]}
        },
        "sender_id": sender_id,
        "recipient_id": uid,
        "created_timestamp": int(time.time()*1000),
    },
})

# Try: event with numeric sender/recipient (not string)
T("v5 numeric:", {
    "request_id": str(uuid.uuid4()),
    "event": {
        "type": "MessageCreate",
        "message_data": {"text": "v5"},
        "sender_id": int(sender_id),
        "recipient_id": int(uid),
        "created_timestamp": int(time.time()*1000),
    },
})

# Try without dark header — plain
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
    headers={"content-type":"application/json","authorization":"Bearer "+s._s.headers if False else "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"},
    json={"request_id":str(uuid.uuid4()),"event":{"type":"MessageCreate","message_data":{"text":"v6"},"recipient_id":uid}})
print("v6 minimal hdr:", r.status_code, r.text[:400])
