import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
a = accs[0]
s = XSessionLite(a["auth_token"], ct0=a["ct0"])
s.authenticate()
uid, res = s.lookup_user_id("Zxbc16f7")
print("=== Zxbc16f7 ===")
print(json.dumps(res, indent=2, ensure_ascii=False)[:2500])
