import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
a0 = accs[0]; a1 = accs[1]
s0 = XSessionLite(a0["auth_token"], ct0=a0["ct0"])
s0.authenticate()
s1 = XSessionLite(a1["auth_token"], ct0=a1["ct0"])
s1.authenticate()
QID = "MSIb-PAcnu9OBUe56f_DHQ"
FEAT = {"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"longform_notetweets_consumption_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"view_counts_everywhere_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"rweb_video_timestamps_enabled":True,"responsive_web_enhance_cards_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"communities_web_enable_tweet_community_results_fetch":True,"articles_preview_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False}
def notifs(s):
    url = f"https://x.com/i/api/graphql/{QID}/NotificationsTimeline"
    params = {"variables": json.dumps({"count":30,"includePromotedContent":False,"timeline_type":"All"}),
              "features": json.dumps(FEAT)}
    r = s.graphql_get(url, params, "https://x.com/i/notifications")
    return ((r.json().get("data",{}).get("success",{}) or {}).get("entry_list",[]))

print("before:", len(notifs(s0)))
r = s1.follow("gkay_ozan")
print("follow:", r.status_code, r.json().get("following"))
r = s1.create_tweet(f"@gkay_ozan m{int(time.time())}")
print("mention:", r.status_code, r.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id"))
time.sleep(3)
lst = notifs(s0)
print("after:", len(lst))
for e in lst[:10]:
    content = e.get("content",{})
    item = content.get("item") or {}
    print(" ", e.get("entry_id"), "->", json.dumps(item)[:250])
