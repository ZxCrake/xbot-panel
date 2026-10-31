import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")

# follow with each of the 5 accounts (each follow = new notif on Zxbc16f7)
for i,a in enumerate(accs):
    print("=== account", i, a["username"])
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            print("  auth FAIL"); continue
        r = s.follow("Zxbc16f7")
        j = r.json()
        print("  follow:", r.status_code, "following:", j.get("following"))
    except Exception as e:
        print("  ERR:", e)

# now mention with each account (a fresh tweet per account)
print("--- mentions ---")
for i,a in enumerate(accs):
    print("=== account", i, a["username"])
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            print("  auth FAIL"); continue
        r = s.create_tweet(f"@Zxbc16f7 {int(time.time())}-{i}")
        print("  create:", r.status_code, r.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id"))
    except Exception as e:
        print("  ERR:", e)

# activity (notifications) for the 1st account
print("--- activity ---")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
r = s._s.get("https://x.com/i/api/2/activities/all.json?",
             headers=s.headers("GET","/i/api/2/activities/all.json","https://x.com/i/notifications"))
print("act:", r.status_code, r.text[:400])
