import sys, re, json
sys.stdout.reconfigure(encoding="utf-8")
d = open("sandbox/_notifs_raw.json", encoding="utf-8").read()
for label, pat in [
  ("typename", r'"__typename":\s*"([^"]+)"'),
  ("element", r'"element":\s*"([^"]+)"'),
  ("itemType", r'"itemType":\s*"([^"]+)"'),
]:
    found = sorted(set(re.findall(pat, d)))
    print(label+":", found)
print("mention occurrences:", d.lower().count("mention"))
