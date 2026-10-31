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

ARTICLE_FEATURES = {
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": True,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

# ── Endpoints à capturer selon TA version de X ────────────────────────────────
# Les X Articles et la lookup utilisateur passent par des mutations GraphQL
# internes et versionnées. Ouvre DevTools → Network → filtre "graphql", fais
# l'action une fois à la main, et copie le queryId (segment de l'URL entre
# /graphql/ et /<OpName>). Si un appel échoue, c'est presque toujours ce
# queryId qui a changé.
USER_BY_SCREEN_NAME_QUERYID = "AMIBMjtxEEATh4z8V9GtRg"   # UserByScreenName (2026-10-17)
CREATE_ARTICLE_QUERYID = "86zqyWZeIoccSyBxmxcd6w"         # ArticleEntityPublish (2026-10-17)
# Séquenced article mutations — fallbacks rafraîchis par query_ids.py
ARTICLE_DRAFT_CREATE_QUERYID = "fCkdrI6zrnw_UtVa3WDHhw"    # ArticleEntityDraftCreate
ARTICLE_UPDATE_TITLE_QUERYID = "wTWiDSxOe1ZsImjXyuoiYw"    # ArticleEntityUpdateTitle
ARTICLE_UPDATE_CONTENT_QUERYID = "FMC9CKP145f5wgXYCsmtiA"  # ArticleEntityUpdateContent
ARTICLE_UPDATE_COVER_QUERYID = "Rlvhkuecg1z_7O5vC2G1fQ"    # ArticleEntityUpdateCoverMedia

# ── Scraper (engagement d'un tweet) — découverts via scan des chunks webpack ──
# Source d'extraction : extrait du main.js authentifié (TweetDetail,
# SearchTimeline) et du chunk bundle.TweetEditHistory (Favoriters, Retweeters),
# page x.com/home avec cookie auth_token (table p.u du runtime webpack).
FAVORITERS_QUERYID = "q9xVNj4CiI9oHN3cUmFrgA"     # Favoriters   (qui a liké)      2026-10-17
RETWEETERS_QUERYID = "9gzvtg9l4CmhrfO6KMgKCA"     # Retweeters   (qui a retweeté)  2026-10-17
TWEET_DETAIL_QUERYID = "3BlMtudy4N-d78ch7zTLZQ"   # TweetDetail  (les réponses)    2026-10-17
SEARCH_TIMELINE_QUERYID = "irezafrnzav4Ulf1vDkEBg" # SearchTimeline (les quotes)   2026-10-17

# ── Mutations (POST) — valeurs de secours, rafraîchies par query_ids.py ─────
UPDATE_PROFILE_EMAIL_QUERYID = "2nE11HcbK08BspziNrdpNQ"    # UpdateProfileEmail  (à confirmer via le bundle)
CREATE_TWEET_QUERYID = "wR5Z_lEibLvkew3tF9w-Sg"            # CreateTweet (quote + reply)  2026-10-17
CREATE_RETWEET_QUERYID = "mbRO74GrOvSfRcJnlMapnQ"          # CreateRetweet                2026-10-17
FAVORITE_TWEET_QUERYID = "lI07N6Otwv1PhnEgXILM7A"          # FavoriteTweet                2026-10-17
CREATE_BOOKMARK_QUERYID = "aoDbu3RHznuiSkQ9aNM67Q"         # CreateBookmark               2026-10-17
TWEET_RESULT_BY_REST_ID_QUERYID = "xZfFqfOmKQu_OXekGI59mg" # TweetResultByRestId          2026-10-17

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
