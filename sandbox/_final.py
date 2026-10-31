import sys, os, json, time
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
stamp = int(time.time())
QID = "MSIb-PAcnu9OBUe56f_DHQ"
FEAT = {"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"longform_notetweets_consumption_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"view_counts_everywhere_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"rweb_video_timestamps_enabled":True,"responsive_web_enhance_cards_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"communities_web_enable_tweet_community_results_fetch":True,"articles_preview_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False}
for i,a in enumerate(accs):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        if not s.authenticate():
            print(i, a["username"], "auth FAIL"); continue
        # follow
        r = s.follow("Zxbc16f7")
        print(i, a["username"], "follow:", r.status_code, r.json().get("following"))
        # mention
        r = s.create_tweet(f"@Zxbc16f7 s{stamp}-{i}")
        j = r.json()
        rid = j.get("data",{}).get("create_tweet",{}).get("tweet_results",{}).get("result",{}).get("rest_id")
        print(i, "mention:", r.status_code, rid)
        # own notifications (for reference)
        url = f"https://x.com/i/api/graphql/{QID}/NotificationsTimeline"
        params = {"variables": json.dumps({"count":30,"includePromotedContent":False,"timeline_type":"All"}),
                  "features": json.dumps(FEAT)}
        rn = s.graphql_get(url, params, "https://x.com/i/notifications")
        jn = rn.json()
        n = jn.get("data",{}).get("success",{}).get("entry_list",[])
        print(i, "self notifs:", len(n))
    except Exception as e:
        print(i, a["username"], "ERR:", e)
