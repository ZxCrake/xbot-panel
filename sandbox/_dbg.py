import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
from curl_cffi import requests as cr
from x_client_transaction.utils import get_ondemand_file_url
import bs4

accs = load_accounts("sandbox/account.txt")
for i in (4,5,6,7,8,9):
    a = accs[i]
    print("===", i, a["username"], "auth:", a["auth_token"])
    s = cr.Session(impersonate="chrome124", timeout=20)
    r = s.get("https://x.com/home", headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "cookie": f"auth_token={a['auth_token']}",
    })
    print(" HTTP", r.status_code, "len", len(r.text))
    if r.status_code == 200:
        soup = bs4.BeautifulSoup(r.content, "html.parser")
        u = get_ondemand_file_url(response=soup)
        print(" od url:", u)
        # check if there's an error message
        m = r.text[:400]
        print(" snippet:", m)
    else:
        print(" body:", r.text[:400])
    s.close()
