import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
stamp = int(time.time())
for i,a in enumerate(accs):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate(): print(i, a["username"], "auth FAIL"); continue
        r = s.follow("Zxbc16f7")
        rf = r.json()
        r2 = s.create_tweet(f"@Zxbc16f7 {stamp}-{i}")
        j2 = r2.json()
        rid = j2.get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id")
        print(i, a["username"], "follow:", rf.get("following"), "mention:", rid)
    except Exception as e:
        print(i, a["username"], "ERR:", str(e)[:100])
