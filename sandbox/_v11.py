import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts, TWEET_FEATURES, CREATE_TWEET_QID
accs = load_accounts("sandbox/account.txt")
a = accs[0]
s = XSessionLite(a["auth_token"], ct0=a["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
stamp = int(time.time())

# --- 1) REST v1.1 statuses/update.json (form) ---
h = s.headers("POST","/i/api/1.1/statuses/update.json","https://x.com/home")
h["content-type"] = "application/x-www-form-urlencoded"
r = s._s.post("https://x.com/i/api/1.1/statuses/update.json",
    headers=h,
    data={"status": f"@Zxbc16f7 rest {stamp}", "include_entities": "true"})
print("v1.1:", r.status_code, r.text[:400])

# --- 2) GraphQL with explicit entities.user_mentions ---
url = f"https://x.com/i/api/graphql/{CREATE_TWEET_QID}/CreateTweet"
payload = {"variables": {
    "tweet_text": f"@Zxbc16f7 ent {stamp}",
    "dark_request": False,
    "media": {"media_entities": [], "possibly_sensitive": False},
    "semantic_annotation_ids": [],
    "disallowed_reply_options": None,
    "entities": {"user_mentions": [{"id_str": uid, "indices": [0, 9]}], "urls": [], "hashtags": []},
  },
  "features": TWEET_FEATURES, "queryId": CREATE_TWEET_QID}
r = s.graphql_post(url, payload, "https://x.com/compose/post")
print("entities:", r.status_code, r.text[:400])
