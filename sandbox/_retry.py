import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
stamp = int(time.time())
# retry the failed ones
for idx in (1, 4):
    a = accs[idx]
    print("=== account", idx, a["username"], "auth_token:", a["auth_token"])
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        ok = s.authenticate()
        print(" auth:", ok)
        r = s.follow("Zxbc16f7")
        rf = r.json()
        print(" follow:", r.status_code, rf.get("following"))
        r2 = s.create_tweet(f"@Zxbc16f7 n{stamp} a{idx}")
        j2 = r2.json()
        print(" mention:", r2.status_code, j2.get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id"))
    except Exception as e:
        print(" ERR:", e)
