import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
a = accs[0]
s = XSessionLite(a["auth_token"], ct0=a["ct0"])
s.authenticate()
QID = "MSIb-PAcnu9OBUe56f_DHQ"
FEAT = {"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"longform_notetweets_consumption_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"view_counts_everywhere_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"rweb_video_timestamps_enabled":True,"responsive_web_enhance_cards_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"communities_web_enable_tweet_community_results_fetch":True,"articles_preview_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False}
url = f"https://x.com/i/api/graphql/{QID}/NotificationsTimeline"
params = {"variables": json.dumps({"count":30,"includePromotedContent":False,"timeline_type":"All"}),
          "features": json.dumps(FEAT)}
r = s.graphql_get(url, params, "https://x.com/i/notifications")
j = r.json()
ins = j["data"]["viewer_v2"]["user_results"]["result"]["notification_timeline"]["timeline"]["instructions"]
open("sandbox/_notifs_raw.json","w",encoding="utf-8").write(json.dumps(j,indent=2,ensure_ascii=False))
for instr in ins:
    for e in instr.get("entries",[]):
        c = e.get("content",{})
        ic = c.get("itemContent",{}) or {}
        if ic.get("__typename") != "TimelineNotification": continue
        cev = (c.get("clientEventInfo") or {})
        meta = ((cev.get("details") or {}).get("notificationDetails") or {}).get("metadata","")
        el = cev.get("element") or ""
        rich = ic.get("rich_message",{}) or {}
        parts = []
        for ent in rich.get("entities",[]):
            ref = ent.get("ref",{}) or {}
            if "user_results" in ref:
                parts.append(ref["user_results"].get("result",{}).get("legacy",{}).get("screen_name") or "?")
            elif "type" in ref and ref.get("type") == "TimelineRichTextLink":
                parts.append("LINK:"+ref.get("text","?"))
        # also try top-level for old format
        legacy = (ic.get("legacy") or {})
        print(e.get("entryId",""), "|", el, "|meta:", meta[:60] if meta else "", "|parts:", parts)
print("saved to sandbox/_notifs_raw.json")
