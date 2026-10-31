import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
stamp = int(time.time())
results = []
for i,a in enumerate(accs):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            results.append((i, a["username"], "auth FAIL")); continue
        r = s.follow("Zxbc16f7")
        rf = r.json()
        r2 = s.create_tweet(f"@Zxbc16f7 n{stamp} a{i}")
        j2 = r2.json()
        rid = j2.get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id")
        results.append((i, a["username"], f"follow={rf.get('following')} mention={rid}"))
    except Exception as e:
        results.append((i, a["username"], f"ERR {e}"))
for r in results: print(r)
