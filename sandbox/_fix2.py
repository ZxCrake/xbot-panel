p = "sandbox/post_tweet.py"
s = open(p, encoding="utf-8").read()
# add json_post right after form_post definition
marker = "        return self._s.post(url, headers=headers, data=data)"
addition = marker + "\n\n    def json_post(self, url, payload, referer):\n        headers = self.headers(\"POST\", self._path(url), referer)\n        headers[\"content-type\"] = \"application/json\"\n        return self._s.post(url, headers=headers, json=payload)"
if "def json_post" not in s:
    s = s.replace(marker, addition, 1)
open(p, "w", encoding="utf-8").write(s)
print("json_post added" if "def json_post" in open(p, encoding="utf-8").read() else "FAIL")
