"""Scan read-only des bundles X pour trouver les opérations liées à l'e-mail.

À exécuter depuis la racine du projet (serveur Linux) :
    .venv/bin/python -I tools/_scan_ops.py

N'affiche aucun secret : seule la première ligne de accounts.txt est lue
pour le cookie d'authentification.
"""
import os
import re
import glob
import concurrent.futures as cf

from curl_cffi import requests

BASE = "https://abs.twimg.com/responsive-web/client-web/"


def auth_token():
    for path in glob.glob("data/users/*/accounts.txt"):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    return line.split(":")[-1]
    return ""


S = requests.Session(impersonate="chrome124")
tok = auth_token()
if tok:
    S.headers["Cookie"] = f"auth_token={tok}"

t = S.get("https://x.com/settings/profile", timeout=30).text
blocks = re.findall(r"<script[^>]*>(.*?)</script>", t, re.S)
big = next((b for b in blocks if "t.u=e=>" in b), "")
if not big:
    t = S.get("https://x.com/home", timeout=30).text
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", t, re.S)
    big = next((b for b in blocks if "t.u=e=>" in b), "")
print("map trouvée:", bool(big), "| html:", len(t))

seg = big[big.index("t.u=e=>"):]
e1 = seg.index("})")
names = dict(re.findall(r'(\d+):"([\w.~-]+)"', seg[:e1 + 1]))
n2 = seg.index("{", e1)
e2 = seg.index("})", n2)
hashes = dict(re.findall(r'(\d+):"([0-9a-f]+)"', seg[n2:e2 + 1]))
print("chunks:", len(names), "| hashes:", len(hashes))

urls = set()
for cid, h in hashes.items():
    urls.add(f"{BASE}{cid}.{h}a.js")
    if cid in names:
        urls.add(f"{BASE}{names[cid]}.{h}a.js")
# runtime principal
for m in re.finditer(r'https://abs\.twimg\.com/responsive-web/client-web/[\w.]+\.js', t):
    urls.add(m.group(0))
urls = sorted(urls)
print("URLs à scanner:", len(urls))


def scan(url):
    try:
        js = S.get(url, timeout=25).text
    except Exception:
        return url, []
    found = []
    for m in re.finditer(r'queryId:"([\w-]+)",operationName:"(\w+)"', js):
        found.append((m.group(2), m.group(1)))
    for m in re.finditer(r'operationName:"(\w+)"', js):
        name = m.group(1)
        if re.search(r"mail", name, re.I):
            ctx = js[max(0, m.start() - 120):m.end() + 60]
            q = re.search(r'queryId:"([\w-]+)"', ctx)
            found.append((name, q.group(1) if q else "?"))
    # endpoints REST contenant email
    for m in re.finditer(r'"(account/[\w_]*email[\w_]*|[\w/]*email[\w_]*)\.json"', js):
        found.append(("REST:" + m.group(1), url.split("/")[-1]))
    return url, found


hits = {}
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for url, found in ex.map(scan, urls):
        for name, qid in found:
            if re.search(r"mail", name, re.I):
                hits.setdefault((name, qid), url)

print("\n=== OPÉRATIONS E-MAIL TROUVÉES ===")
if not hits:
    print("aucune")
for (name, qid), url in sorted(hits.items()):
    print(f"{name:38} {qid:28} {url.split('/')[-1]}")
