import json, sys
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open("sandbox/_notifs_raw.json", encoding="utf-8"))
ins = d["data"]["viewer_v2"]["user_results"]["result"]["notification_timeline"]["timeline"]["instructions"]
for instr in ins:
    for e in instr.get("entries",[]):
        c = e.get("content",{})
        ic = c.get("itemContent",{}) or {}
        cev = (c.get("clientEventInfo") or {})
        el = cev.get("element") or ""
        print(el, "|", json.dumps(ic, ensure_ascii=False)[:250])
        print("--")
