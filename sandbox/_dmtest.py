import sys, os, json, time, uuid
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts, BASE_UA_HEADERS, BEARER_TOKEN
from curl_cffi import requests as cr

accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
print("uid:", uid)
stamp = str(int(time.time()))

# A: json body
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
    headers=s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"),
    json={"request_id": str(uuid.uuid4()), "event": {"type":"MessageCreate","message_data":{"text": stamp, "entities":{}},"recipient_id":uid,"created_timestamp":int(time.time()*1000)}})
print("A json:", r.status_code, r.text[:200])

# B: json body without request_id
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
    headers=s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"),
    json={"event": {"type":"MessageCreate","message_data":{"text": stamp+"b", "entities":{}},"recipient_id":uid,"created_timestamp":int(time.time()*1000)}})
print("B json no-req:", r.status_code, r.text[:200])

# C: form
r = s._s.post("https://x.com/i/api/1.1/dm/new2.json",
    headers={**s.headers("POST","/i/api/1.1/dm/new2.json", f"https://x.com/messages/{uid}"), "content-type":"application/x-www-form-urlencoded"},
    data={"request_id": str(uuid.uuid4()), "event": json.dumps({"type":"MessageCreate","message_data":{"text": stamp+"c","entities":{}},"recipient_id":uid})})
print("C form:", r.status_code, r.text[:200])
