import sys, os, json
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
QID = "xZfFqfOmKQu_OXekGI59mg"
FEAT = {"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"longform_notetweets_consumption_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"view_counts_everywhere_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"rweb_video_timestamps_enabled":True,"responsive_web_enhance_cards_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"communities_web_enable_tweet_community_results_fetch":True,"articles_preview_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False}
def lookup(rid):
    url = f"https://x.com/i/api/graphql/{QID}/TweetResultByRestId"
    params = {"variables": json.dumps({"tweetId":rid,"withCommunity":False,"includePromotedContent":False,"withVoice":False}),
              "features": json.dumps(FEAT)}
    r = s.graphql_get(url, params, "https://x.com/i/status/"+rid)
    j = r.json()
    return j.get("data",{}).get("tweetResult",{}).get("result",{})

for rid in ["2113985994945110261","2113986004315172927","2113986066470592954"]:
    res = lookup(rid)
    print("---", rid)
    print(" __typename:", res.get("__typename"))
    print(" tombstone:", "tombstone" in res)
    print(" mentions:", res.get("legacy",{}).get("entities",{}).get("user_mentions"))
    print(" conversation_count:", res.get("legacy",{}).get("conversation_count"))
