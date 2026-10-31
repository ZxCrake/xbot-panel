import json, urllib.request
u="https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/v1.1.json"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    d=json.loads(r.read().decode())
for item in d:
    if "new" in str(item.get("queryId","")).lower() or "add_to" in str(item.get("queryId","")).lower():
        print(item)
