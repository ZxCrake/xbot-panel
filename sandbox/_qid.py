import json, urllib.request
url = "https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/API.json"
req = urllib.request.Request(url, headers={"User-Agent":"x/1.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    doc = json.loads(r.read().decode())
g = doc.get("graphql", {})
for k,v in g.items():
    if "dm" in k.lower() or "DM" in k or "message" in k.lower() or "Direct" in k:
        print(k, v.get("queryId") if isinstance(v, dict) else "")
