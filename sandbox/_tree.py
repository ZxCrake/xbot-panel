import urllib.request
u="https://api.github.com/repos/fa0311/TwitterInternalAPIDocument/git/trees/develop?recursive=1"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
    import json
    d=json.loads(r.read())
    for t in d.get("tree",[]):
        p=t["path"]
        if "dm" in p.lower() or "message" in p.lower() or "1.1" in p:
            print(p)
