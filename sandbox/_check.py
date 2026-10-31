import sys, os, json
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
# Read last created tweet
url = "https://x.com/i/api/graphql/xZfFqfOmKQu_OXekGI59mg/TweetResultByRestId"
import json as J
params = {
    "variables": J.dumps({"tweetId":"2113980868582666544","withCommunity":False,"includePromotedContent":False,"withVoice":False}),
    "features": J.dumps({
        "creator_subscriptions_tweet_preview_api_enabled":True,
        "communities_web_enable_tweet_community_results_fetch":True,
        "c9s_tweet_anatomy_moderator_badge_enabled":True,
        "articles_preview_enabled":True,
        "responsive_web_edit_tweet_api_enabled":True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,
        "view_counts_everywhere_api_enabled":True,
        "longform_notetweets_consumption_enabled":True,
        "responsive_web_twitter_article_tweet_consumption_enabled":True,
        "tweet_awards_web_tipping_enabled":False,
        "creator_subscriptions_quote_tweet_preview_enabled":False,
        "freedom_of_speech_not_reach_fetch_enabled":True,
        "standardized_nudges_misinfo":True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,
        "rweb_video_timestamps_enabled":True,
        "longform_notetweets_rich_text_read_enabled":True,
        "longform_notetweets_inline_media_enabled":True,
        "responsive_web_graphql_timeline_navigation_enabled":True,
        "responsive_web_enhance_cards_enabled":False,
    }),
}
r = s.graphql_get(url, params, "https://x.com/i/status/2113980868582666544")
j = r.json()
res = j["data"]["tweetResult"]["result"]
print("__typename:", res.get("__typename"))
print("has tombstone:", "tombstone" in res)
print("legacy created:", res.get("legacy",{}).get("created_at"))
print("entities:", json.dumps(res.get("legacy",{}).get("entities",{}), ensure_ascii=False)[:500])
