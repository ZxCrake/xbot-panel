import urllib.request
urls = [
    "https://raw.githubusercontent.com/fa0311/TwitterInternalAPIDocument/refs/heads/develop/docs/en/direct_message.md",
]
for u in urls:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"x/1.0"}), timeout=15) as r:
            txt = r.read().decode()
        print("===",u)
        print(txt[:3000])
    except Exception as e:
        print("err:", u, e)
