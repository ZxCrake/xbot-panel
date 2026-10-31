p = "sandbox/post_tweet.py"
s = open(p, encoding="utf-8").read()
old = """        data = {
            "request_id": str(uuid.uuid4()),
            "recipient_id": str(recipient_id),
            "text": text,
            "cards_platform": "Web-12",
            "include_cards": "0",
            "include_quote_count": "false",
            "dm_users": "false",
        }"""
new = """        data = {
            "request_id": str(uuid.uuid4()),
            "recipient_id": str(recipient_id),
            "text": text,
            "cards_platform": "Web-12",
            "include_cards": False,
            "include_quote_count": False,
            "dm_users": False,
        }"""
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
