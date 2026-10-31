import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
for i,a in enumerate(accs):
    print("=== account", i, a["username"])
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        ok = s.authenticate()
        print(" auth:", "OK" if ok else "FAIL")
        if not ok: continue
        # verify_credentials to see state
        r = s._s.get("https://x.com/i/api/1.1/account/verify_credentials.json",
                     headers=s.headers("GET","/i/api/1.1/account/verify_credentials.json","https://x.com/home"))
        v = r.json()
        print(" self:", v.get("screen_name"), "following:", v.get("friends_count"))
        # does it already follow Zxbc16f7?
        r = s._s.get(f"https://x.com/i/api/1.1/friendships/chain.json?user_id=2104863214701826048",
                     headers=s.headers("GET","/i/api/1.1/friendships/chain.json","https://x.com/Zxbc16f7"))
        print(" chain:", r.status_code, r.text[:200])
        # try follow
        r = s.follow("Zxbc16f7")
        j = r.json()
        print(" follow:", r.status_code, "following:", j.get("following"), "follow_request_sent:", j.get("follow_request_sent"))
    except Exception as e:
        print(" ERR:", e)
