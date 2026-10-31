import json, urllib.request
u="https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/v1.1.json"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    d=json.loads(r.read().decode())
# find items where name/id has "new2" or "dm/"
for item in d:
    if not isinstance(item, dict): continue
    blob = json.dumps(item, ensure_ascii=False)
    if "/dm/new2" in blob or "/dm/init" in blob or "new2" in blob[:400]:
        print(json.dumps(item, ensure_ascii=False)[:800])
        print("---")
