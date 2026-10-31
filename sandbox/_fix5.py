p = "sandbox/post_tweet.py"
s = open(p, encoding="utf-8").read()
old = """    def send_dm(self, recipient_id, text):
        import uuid, time
        url = "https://x.com/i/api/1.1/dm/new2.json"
        data = {
            "request_id": str(uuid.uuid4()),
            "event": {
                "type": "MessageCreate",
                "message_data": {"text": text, "entities": {}},
                "sender_id": None,
                "recipient_id": str(recipient_id),
                "created_timestamp": int(time.time() * 1000),
            },
        }
        return self.json_post(url, data, f"https://x.com/messages/{recipient_id}")"""
new = """    def send_dm(self, recipient_id, text):
        import uuid, time, json as _j
        url = "https://x.com/i/api/1.1/dm/new2.json"
        event = {
            "type": "MessageCreate",
            "message_data": {"text": text, "entities": {}},
            "recipient_id": str(recipient_id),
            "created_timestamp": int(time.time() * 1000),
        }
        data = {
            "request_id": str(uuid.uuid4()),
            "event": _j.dumps(event),
        }
        return self.form_post(url, data, f"https://x.com/messages/{recipient_id}")"""
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
