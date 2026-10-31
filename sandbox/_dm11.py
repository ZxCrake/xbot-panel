import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")

def raw(url, body_str, ctype="application/x-www-form-urlencoded"):
    path = url.split("x.com",1)[-1]
    h = s.headers("POST", path, "https://x.com/home")
    h["content-type"] = ctype
    return s._s.post(url, headers=h, data=body_str)

# raw form string
r = raw("https://x.com/i/api/1.1/dm/new2.json",
        "recipient_id=" + uid + "&text=rawform&request_id=" + str(uuid.uuid4()))
print("rawform:", r.status_code, r.text[:300])

# json body sent as raw string
r = raw("https://x.com/i/api/1.1/dm/new2.json",
        json.dumps({"request_id": str(uuid.uuid4()), "event": {"type":"MessageCreate","message_data":{"text":"rawjson","entities":{}},"recipient_id":uid}}),
        ctype="application/json")
print("rawjson:", r.status_code, r.text[:300])

# json body sent as raw string, but as `variables=<json>` form field
r = raw("https://x.com/i/api/1.1/dm/new2.json",
        "variables=" + json.dumps({"request_id":str(uuid.uuid4()),"event":{"type":"MessageCreate","message_data":{"text":"varjson","entities":{}},"recipient_id":uid}}))
print("variablesform:", r.status_code, r.text[:300])

# json body sent with `event=<json>` form field
r = raw("https://x.com/i/api/1.1/dm/new2.json",
        "request_id=" + str(uuid.uuid4()) + "&event=" + json.dumps({"type":"MessageCreate","message_data":{"text":"evt","entities":{}},"recipient_id":uid}))
print("eventform:", r.status_code, r.text[:300])
