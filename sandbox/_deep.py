import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
a = accs[0]
s = XSessionLite(a["auth_token"], ct0=a["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")

# try each notification type on same account
stamp = int(time.time())

# 1) plain mention
r = s.create_tweet(f"@Zxbc16f7 n{stamp}")
print("mention:", r.status_code, r.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id"))

time.sleep(1)

# 2) reply to it from a different account (CChimkande), still with mention
b = accs[1]
s2 = XSessionLite(b["auth_token"], ct0=b["ct0"])
s2.authenticate()
first = r.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id")
if first:
    r2 = s2.create_tweet(f"@Zxbc16f7 r{stamp}", reply_to=first)
    print("reply-from-other:", r2.status_code, r2.json().get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id"))

# 3) Check the source's own NotificationsTimeline to see if anything new
QID = "MSIb-PAcnu9OBUe56f_DHQ"
FEAT = {"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"longform_notetweets_consumption_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"view_counts_everywhere_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"rweb_video_timestamps_enabled":True,"responsive_web_enhance_cards_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"communities_web_enable_tweet_community_results_fetch":True,"articles_preview_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False}
url = f"https://x.com/i/api/graphql/{QID}/NotificationsTimeline"
for tt in ("All","Mentions","Verified"):
    params = {"variables": json.dumps({"count":30,"includePromotedContent":False,"timeline_type":tt}),
              "features": json.dumps(FEAT)}
    rr = s.graphql_get(url, params, "https://x.com/i/notifications")
    jj = rr.json()
    n = (jj.get("data",{}).get("success",{}) or {}).get("entry_list",[])
    print(f"{tt}: {len(n)} entries", "first:", (n[0].get('content',{}).get('item') or {}) if n else None)
