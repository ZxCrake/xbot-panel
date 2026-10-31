import re
p="sandbox/post_tweet.py"
s=open(p,encoding="utf-8").read()
# Fix 1: sync ct0 always (remove the `if not self._ct0:` wrapper)
s=s.replace("        if not self._ct0:\n","        # sync ct0 (file value may be stale)\n",1)
# The body already at 12 spaces indent from the if, dedent block: we need to remove 4 spaces on lines that start with 12 spaces in that region.
# Simpler: rebuild whole block manually
new_block=(
'''        # sync ct0 from session cookie jar (file value may be stale)
        r = self._s.post(
            "https://x.com/i/api/1.1/account/update_profile.json",
            headers={
                **BASE_UA_HEADERS,
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://x.com",
                "priority": "u=1, i",
                "referer": "https://x.com/settings/profile",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-twitter-active-user": "yes",
                "x-twitter-auth-type": "OAuth2Session",
                "x-twitter-client-language": "en",
                "cookie": self.cookie(),
            },
        )
        self._ct0 = r.cookies.get("ct0", self._ct0)
''')
# find old block boundaries
i1=s.index("        # sync ct0 from session cookie jar")
i2=s.index('        self._ct0 = r.cookies.get("ct0", "")')
i2=s.index("\n",i2)+1
s=s[:i1]+new_block+s[i2:]
open(p,"w",encoding="utf-8").write(s)
print("OK")
