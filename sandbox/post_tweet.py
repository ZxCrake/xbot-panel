import os
import sys
import json
import bs4
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from curl_cffi import requests as curl_requests
from x_client_transaction.utils import get_ondemand_file_url
from x_client_transaction import ClientTransaction

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
XPFF_BASE_KEY = "0e6be1f1e21ffc33590b888fd4dc81b19713e570e805d4e5df80a493c9571a05"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

BASE_UA_HEADERS = {
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"142.0.7444.60"',
    "sec-ch-ua-full-version-list": '"Chromium";v="142.0.7444.60", "Google Chrome";v="142.0.7444.60", "Not_A Brand";v="99.0.0.0"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "user-agent": USER_AGENT,
    "accept-language": "en-US,en;q=0.9",
}

TWEET_FEATURES = {
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "payments_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": True,
    "verified_phone_label_enabled": False,
    "articles_preview_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

CREATE_TWEET_QID = "wR5Z_lEibLvkew3tF9w-Sg"
USER_BY_SCREEN_NAME_QID = "AMIBMjtxEEATh4z8V9GtRg"


def load_accounts(path):
    accounts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("format:"):
                continue
            parts = line.split(":")
            if len(parts) < 5:
                continue
            accounts.append({
                "username": parts[0],
                "password": parts[1],
                "email": parts[2],
                "ct0": parts[3],
                "auth_token": parts[4],
            })
    return accounts


class XSessionLite:
    def __init__(self, auth_token, ct0="", proxy=""):
        self.auth_token = auth_token
        self._s = curl_requests.Session(
            impersonate="chrome124",
            proxies={"http": proxy, "https": proxy} if proxy else {},
            timeout=30,
        )
        self._ct0 = ct0
        self._gt = ""
        self._xpff = ""
        self._ct = None
        self._cookie_base = {}

    def cookie(self):
        parts = dict(self._cookie_base)
        if self._ct0:
            parts["ct0"] = self._ct0
        if self._gt:
            parts["gt"] = self._gt
        return "; ".join(f"{k}={v}" for k, v in parts.items() if v)

    def headers(self, method, path, referer):
        return {
            **BASE_UA_HEADERS,
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "authorization": f"Bearer {BEARER_TOKEN}",
            "content-type": "application/json",
            "cookie": self.cookie(),
            "origin": "https://x.com",
            "priority": "u=1, i",
            "referer": referer,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-client-transaction-id": self._ct.generate_transaction_id(method=method, path=path),
            "x-csrf-token": self._ct0,
            "x-guest-token": self._gt,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "x-xp-forwarded-for": self._xpff,
        }

    def authenticate(self):
        home = self._s.get("https://x.com/home", headers={
            **BASE_UA_HEADERS,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "cookie": f"auth_token={self.auth_token}",
        })
        sc = dict(self._s.cookies)
        self._cookie_base = {
            "auth_token": self.auth_token,
            "personalization_id": sc.get("personalization_id", ""),
            "guest_id": sc.get("guest_id", ""),
        }
        soup = bs4.BeautifulSoup(home.content, "html.parser")
        od_url = get_ondemand_file_url(response=soup)
        od_text = self._s.get(od_url).text
        self._ct = ClientTransaction(home_page_response=soup, ondemand_file_response=od_text)

        # sync ct0 from session cookie jar (file value may be stale)
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

        r = self._s.post(
            "https://api.x.com/1.1/guest/activate.json",
            headers={
                **BASE_UA_HEADERS,
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "authorization": f"Bearer {BEARER_TOKEN}",
                "content-type": "application/json",
                "cookie": self.cookie(),
                "origin": "https://x.com",
                "referer": "https://x.com/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "x-csrf-token": self._ct0,
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "en",
                "x-client-transaction-id": self._ct.generate_transaction_id(
                    method="POST", path="/1.1/guest/activate.json"),
            },
        )
        self._gt = r.json().get("guest_token", "")

        from xbot.x.xpff import XPFFHeaderGenerator
        gen = XPFFHeaderGenerator(XPFF_BASE_KEY)
        self._xpff, _ = gen.generate(USER_AGENT, self._gt, True)
        return True

    def _path(self, url):
        return url.split("x.com", 1)[-1]

    def graphql_post(self, url, payload, referer):
        headers = self.headers("POST", self._path(url), referer)
        return self._s.post(url, headers=headers, json=payload)

    def graphql_get(self, url, params, referer):
        headers = self.headers("GET", self._path(url), referer)
        return self._s.get(url, headers=headers, params=params)

    def form_post(self, url, data, referer):
        headers = self.headers("POST", self._path(url), referer)
        headers["content-type"] = "application/x-www-form-urlencoded"
        return self._s.post(url, headers=headers, data=data)

    def json_post(self, url, payload, referer):
        headers = self.headers("POST", self._path(url), referer)
        headers["content-type"] = "application/json"
        return self._s.post(url, headers=headers, json=payload)

    def create_tweet(self, text, reply_to=None):
        url = f"https://x.com/i/api/graphql/{CREATE_TWEET_QID}/CreateTweet"
        variables = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "disallowed_reply_options": None,
        }
        referer = "https://x.com/compose/post"
        if reply_to:
            variables["reply"] = {
                "in_reply_to_tweet_id": reply_to,
                "exclude_reply_user_ids": [],
            }
            referer = f"https://x.com/i/status/{reply_to}"
        payload = {
            "variables": variables,
            "features": TWEET_FEATURES,
            "queryId": CREATE_TWEET_QID,
        }
        return self.graphql_post(url, payload, referer)

    def follow(self, screen_name):
        url = "https://x.com/i/api/1.1/friendships/create.json"
        data = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            "include_can_media_tag": "1",
            "include_ext_is_blue_verified": "1",
            "skip_status": "1",
            "screen_name": screen_name,
        }
        return self.form_post(url, data, f"https://x.com/{screen_name}")

    def send_dm(self, recipient_id, text):
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
        return self.form_post(url, data, f"https://x.com/messages/{recipient_id}")

    def lookup_user_id(self, screen_name):
        url = f"https://x.com/i/api/graphql/{USER_BY_SCREEN_NAME_QID}/UserByScreenName"
        params = {
            "variables": json.dumps({
                "screen_name": screen_name,
                "withSafetyModeUserFields": True,
            }),
            "features": json.dumps({
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "responsive_web_twitter_article_notes_tab_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
            }),
        }
        r = self.graphql_get(url, params, f"https://x.com/{screen_name}")
        try:
            result = r.json()["data"]["user"]["result"]
            return (result.get("rest_id") or result.get("id") or ""), result
        except Exception:
            return "", {}


def main():
    import time
    accounts = load_accounts("sandbox/account.txt")
    print(f"Loaded {len(accounts)} accounts")

    chosen = accounts[0]
    sess = XSessionLite(chosen["auth_token"], ct0=chosen["ct0"])
    print("Authenticating...")
    ok = sess.authenticate()
    print("Auth:", "OK" if ok else "FAIL")
    if not ok:
        return

    uid, _ = sess.lookup_user_id("Zxbc16f7")
    print("Zxbc16f7 user_id:", uid)

    stamp = str(int(time.time()))

    r1 = sess.create_tweet(f"@Zxbc16f7 {stamp}")
    print("[CreateTweet] HTTP", r1.status_code)
    reply_to = None
    try:
        res = r1.json()["data"]["create_tweet"]["tweet_results"]["result"]
        reply_to = res.get("rest_id")
        print("  rest_id:", reply_to)
    except Exception as e:
        print("  err:", e, r1.text[:200])

    r2 = sess.follow("Zxbc16f7")
    print("[Follow] HTTP", r2.status_code, r2.text[:200])

    if uid:
        r3 = sess.send_dm(uid, f"{stamp}")
        print("[DM] HTTP", r3.status_code, r3.text[:200])

    if reply_to:
        r4 = sess.create_tweet(f"@Zxbc16f7 {stamp}r", reply_to=reply_to)
        print("[Reply] HTTP", r4.status_code)


if __name__ == "__main__":
    main()

