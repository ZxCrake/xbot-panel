import json, urllib.request
url = "https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/json/API.json"
req = urllib.request.Request(url, headers={"User-Agent":"x/1.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    doc = json.loads(r.read().decode())
print("keys:", list(doc.keys()))
# find new2
for k, v in doc.items():
    if isinstance(v, dict):
        for kk, vv in v.items():
            if "dm/new2" in str(kk):
                print(k, kk, vv)
