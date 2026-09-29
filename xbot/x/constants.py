import os

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
XPFF_BASE_KEY = os.getenv("XPFF_BASE_KEY", "0e6be1f1e21ffc33590b888fd4dc81b19713e570e805d4e5df80a493c9571a05")
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

VIEW_FEATURES = {
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
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

# ── Endpoints à capturer selon TA version de X ────────────────────────────────
# Les X Articles et la lookup utilisateur passent par des mutations GraphQL
# internes et versionnées. Ouvre DevTools → Network → filtre "graphql", fais
# l'action une fois à la main, et copie le queryId (segment de l'URL entre
# /graphql/ et /<OpName>). Si un appel échoue, c'est presque toujours ce
# queryId qui a changé.
USER_BY_SCREEN_NAME_QUERYID = "KybxDj9RrADIITXlGG8kpw"   # UserByScreenName (2026-09-26, main.js)
CREATE_ARTICLE_QUERYID = ""   # ⚠️ REQUIS : capture-le sur une vraie publication d'article

# ── Scraper (engagement d'un tweet) — découverts via scan des chunks webpack ──
# Source d'extraction : extrait du main.js authentifié (TweetDetail,
# SearchTimeline) et du chunk bundle.TweetEditHistory (Favoriters, Retweeters),
# page x.com/home avec cookie auth_token (table p.u du runtime webpack).
FAVORITERS_QUERYID = "a2IHRwTdhkcv0Zt0mI-Vrg"     # Favoriters   (qui a liké)      2026-09-26
RETWEETERS_QUERYID = "uDkA6VZo0_WxiXCKl_7ZTA"     # Retweeters   (qui a retweeté)  2026-09-26
TWEET_DETAIL_QUERYID = "zoF7_t363wZyzylk-BLfZQ"   # TweetDetail  (les réponses)    2026-09-26
SEARCH_TIMELINE_QUERYID = "auLkqtmHqYEpRvflfvLhyQ" # SearchTimeline (les quotes)   2026-09-26

# Features envoyées avec les requêtes de scraping. Si X renvoie une erreur de
# "features", copie l'objet features de la vraie requête capturée ici.
SCRAPE_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
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
    "responsive_web_enhance_cards_enabled": False,
}
