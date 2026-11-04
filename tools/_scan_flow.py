"""Cherche le flow de changement d'e-mail dans les chunks Settings."""
import glob
import re

from curl_cffi import requests

BASE = "https://abs.twimg.com/responsive-web/client-web/"
S = requests.Session(impersonate="chrome124")
for path in glob.glob("data/users/*/accounts.txt"):
    with open(path, encoding="utf-8") as f:
        line = next((ln.strip() for ln in f if ln.strip()), "")
    if line:
        S.headers["Cookie"] = f"auth_token={line.split(':')[-1]}"
        break

t = S.get("https://x.com/settings/profile", timeout=30).text
big = next((b for b in re.findall(r"<script[^>]*>(.*?)</script>", t, re.S)
            if "t.u=e=>" in b), "")
seg = big[big.index("t.u=e=>"):]
e1 = seg.index("})")
names = dict(re.findall(r'(\d+):"([\w.~-]+)"', seg[:e1 + 1]))
n2 = seg.index("{", e1)
e2 = seg.index("})", n2)
hashes = dict(re.findall(r'(\d+):"([0-9a-f]+)"', seg[n2:e2 + 1]))

KW = re.compile(r"change_email|changeEmail|ChangeEmail|flow_name|onboarding/task|/i/flow|"
                r"Flow\"|verify_email|VerifyEmail|email_verification|EmailVerification")
TARGETS = [nm for nm in names.values()
           if "Settings" in nm or "Account" in nm or "flow" in nm.lower()]

print("chunks ciblés:", len(TARGETS))
for cid, nm in names.items():
    if nm not in TARGETS:
        continue
    try:
        js = S.get(f"{BASE}{nm}.{hashes[cid]}a.js", timeout=25).text
    except Exception:
        continue
    hits = list(KW.finditer(js))
    if not hits:
        continue
    print(f"\n########## {nm} ({len(js)}) hits={len(hits)}")
    seen = set()
    for m in hits[:12]:
        s = m.start() // 200
        if s in seen:
            continue
        seen.add(s)
        print("  ...", js[max(0, m.start() - 160):m.start() + 160].replace("\n", " "))
