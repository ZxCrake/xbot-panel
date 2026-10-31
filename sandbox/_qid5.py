import json, urllib.request, io, sys
sys.stdout.reconfigure(encoding="utf-8")
u="https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/API.json"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    d=json.loads(r.read().decode())
g=d["graphql"]
for k,v in g.items():
    if "otif" in k or "ctivity" in k.lower():
        print(k, "->", v.get("queryId"))
