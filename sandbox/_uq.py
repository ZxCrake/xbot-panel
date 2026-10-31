import json, urllib.request
u="https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/API.json"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    d=json.loads(r.read().decode())
g=d["graphql"]
for k,v in g.items():
    if "User" in k and ("Tweets" in k or "Timeline" in k or "ByScreen" in k):
        print(k, "->", v.get("queryId"))
