"""Détaille le payload du moteur de flow (onboarding/task) et le flow add_email."""
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

for cid, nm in names.items():
    if nm not in ("bundle.Settings", "ondemand.SettingsInternals", "bundle.SettingsInternals"):
        continue
    js = S.get(f"{BASE}{nm}.{hashes[cid]}a.js", timeout=25).text
    for kw in ("subtask_inputs", "input_flow_data", "flow_token", "add_email"):
        for m in list(re.finditer(kw, js))[:4]:
            print(f"\n--- {nm} [{kw}] ---")
            print(js[max(0, m.start() - 300):m.start() + 300].replace("\n", " "))
