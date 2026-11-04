"""Extrait le contexte autour des mots-clés e-mail dans le chunk Settings."""
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
if not big:
    t = S.get("https://x.com/home", timeout=30).text
    big = next((b for b in re.findall(r"<script[^>]*>(.*?)</script>", t, re.S)
                if "t.u=e=>" in b), "")
if not big:
    raise SystemExit("carte des chunks introuvable (session non authentifiée ?)")
seg = big[big.index("t.u=e=>"):]
e1 = seg.index("})")
names = dict(re.findall(r'(\d+):"([\w.~-]+)"', seg[:e1 + 1]))
n2 = seg.index("{", e1)
e2 = seg.index("})", n2)
hashes = dict(re.findall(r'(\d+):"([0-9a-f]+)"', seg[n2:e2 + 1]))

wanted = [nm for nm in names.values() if "Settings" in nm or "Internals" in nm]
print("chunks ciblés:", wanted)

blobs = {}
for cid, nm in names.items():
    if nm in wanted:
        url = f"{BASE}{nm}.{hashes[cid]}a.js"
        try:
            blobs[nm] = S.get(url, timeout=25).text
            print(nm, len(blobs[nm]))
        except Exception as e:
            print(nm, "ERR", e)

for nm, js in blobs.items():
    for kw in ("email", "Email"):
        for m in list(re.finditer(kw, js))[:40]:
            ctx = js[max(0, m.start() - 180):m.start() + 180]
            if re.search(r"(mutation|graphql|1\.1|account/|POST|fetch|api)", ctx):
                print(f"\n--- {nm} @{m.start()} ---")
                print(ctx.replace("\n", " "))
