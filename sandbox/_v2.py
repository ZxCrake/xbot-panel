import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts, TWEET_FEATURES, CREATE_TWEET_QID
accs = load_accounts("sandbox/account.txt")
stamp = int(time.time())
print("--- pass ---")
for i,a in enumerate(accs[:4]):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate(): print(i,a["username"],"auth fail"); continue
        # follow (produces users_followed_you)
        s.follow("Zxbc16f7")
        # create + reply to own tweet (produces user_replied_to_your_tweet on 2nd account's session)
        r = s.create_tweet(f"@Zxbc16f7 {stamp}-{i}")
        j = r.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{})
        rid = j.get("rest_id")
        # like it via 1.1 favorite or graphql
        if rid:
            qid_fav = "lI07N6Otwv1PhnEgXILM7A"
            url = f"https://x.com/i/api/graphql/{qid_fav}/FavoriteTweet"
            r2 = s.graphql_post(url, {"variables":{"tweet_id":rid},"queryId":qid_fav}, f"https://x.com/i/status/{rid}")
            print(i, a["username"], "follow/mention/like:", rid, "like:", r2.status_code, r2.text[:100])
        # reply from another account
        if i == 0 and rid:
            s2 = XSessionLite(accs[1]["auth_token"], ct0=accs[1]["ct0"])
            s2.authenticate()
            r3 = s2.create_tweet(f"@Zxbc16f7 reply-{stamp}", reply_to=rid)
            print("  reply from CChimkande:", r3.status_code)
    except Exception as e:
        print(i, "ERR:", e)
