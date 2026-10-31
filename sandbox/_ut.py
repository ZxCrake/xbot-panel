import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
from sandbox.post_tweet import XSessionLite, load_accounts
accs = load_accounts("sandbox/account.txt")
s = XSessionLite(accs[0]["auth_token"], ct0=accs[0]["ct0"])
s.authenticate()
uid, _ = s.lookup_user_id("Zxbc16f7")
print("uid:", uid)
# UserTweets
QID = "Iwnkkngx-JNCtIU5/FUxhA"
# fallback
FEAT = {"responsive_web_graphql_exclude_directive_enabled":True,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"c9s_tweet_anatomy_moderator_badge_enabled":True,"tweetypie_unmention_optimization_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"rweb_video_timestamps_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_enhance_cards_enabled":False}
for qid in ("Iwnkkngx-JNCtIU5/FUxhA","n_dYQd7DEPi767lPA972Yw"):
    url = f"https://x.com/i/api/graphql/{qid}/UserTweets"
    params = {"variables": json.dumps({"userId":uid,"count":20,"includePromotedContent":False,"withQuickPromoteEligibilityTweetFields":True,"withVoice":True,"withV2Timeline":True}),
              "features": json.dumps(FEAT)}
    try:
        r = s.graphql_get(url, params, f"https://x.com/{s._cookie_base}")
    except Exception:
        pass
    r = s.graphql_get(url, params, "https://x.com/Zxbc16f7")
    print("qid", qid, "→", r.status_code, r.text[:400])
    break
