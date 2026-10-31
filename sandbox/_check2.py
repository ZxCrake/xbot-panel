import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts, BASE_UA_HEADERS
from x_client_transaction.utils import get_ondemand_file_url
from x_client_transaction import ClientTransaction
from curl_cffi import requests as cr
import bs4

# fetch notifications for Zxbc16f7 via its own auth_token. But we don't have its token.
# Try the "Notifications" graphql op on each of our 5 accounts (each is a different identity so different notification list).

accs = load_accounts("sandbox/account.txt")
# For each account check: does it follow Zxbc16f7?
for i,a in enumerate(accs):
    print("=== account", i, a["username"])
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            print("  auth FAIL"); continue
        # friendships/show
        r = s._s.get("https://x.com/i/api/1.1/friendships/show.json",
                     headers=s.headers("GET","/i/api/1.1/friendships/show.json","https://x.com"),
                     params={"source_id":"2232650113","target_id":"2104863214701826048"})
        print("  show:", r.status_code, r.text[:200])
    except Exception as e:
        print("  ERR:", e)
