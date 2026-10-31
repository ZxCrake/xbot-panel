import json, urllib.request
u="https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/v1.1.json"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    d=json.loads(r.read().decode())
print("count:", len(d))
print(json.dumps(d[0], ensure_ascii=False)[:400])
print("---")
# grep for dm
for item in d:
    s = json.dumps(item, ensure_ascii=False)
    if "dm" in s.lower()[:600]:
        print(s[:600])
        print("--")
