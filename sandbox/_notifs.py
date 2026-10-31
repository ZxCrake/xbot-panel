import sys, os, json
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
# fetch NotificationsTimeline for each account to see if it received anything
QID = "MSIb-PAcnu9OBUe56f_DHQ"
FEAT = {
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}
for i,a in enumerate(accs[:3]):
    try:
        s = XSessionLite(a["auth_token"], ct0=a["ct0"])
        s.authenticate()
        url = f"https://x.com/i/api/graphql/{QID}/NotificationsTimeline"
        params = {
            "variables": json.dumps({"count":30,"includePromotedContent":False}),
            "features": json.dumps(FEAT),
        }
        r = s.graphql_get(url, params, "https://x.com/i/notifications")
        j = r.json()
        # walk for entries
        try:
            entries = j["data"]["success"]["entry_list"]
        except Exception:
            print(i, a["username"], "shape:", list(j)[:5]); continue
        print(f"=== {a['username']} — {len(entries)} notifs")
        for e in entries[:12]:
            content = e.get("content", {})
            summ = content.get("summary") or e.get("sortIndex")
            item = content.get("item", {}) or {}
            line = item.get("summary_text") or ""
            # also try to fetch nested
            print(" ", e.get("entry_id"), "|", line[:100])
    except Exception as ex:
        print(i, "ERR", ex)
