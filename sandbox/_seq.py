import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
print("uid:", uid)

# do follow first (this should register Zxbc16f7 as followed)
r = s.follow("Zxbc16f7")
print("[Follow] HTTP", r.status_code, r.text[:180])

# then create tweet with mention
stamp = str(int(time.time()))
r = s.create_tweet(f"@Zxbc16f7 {stamp}")
print("[CreateTweet] HTTP", r.status_code)
j = r.json()
print(json.dumps(j, ensure_ascii=False)[:1200])

# then reply to it
res = j["data"]["create_tweet"]["tweet_results"]["result"]
rest_id = res.get("rest_id")
r = s.create_tweet(f"@Zxbc16f7 {stamp}r", reply_to=rest_id)
print("[Reply] HTTP", r.status_code, r.text[:400])
