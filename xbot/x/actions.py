import json
import base64
import uuid
from .session import XSession
from .constants import (
    TWEET_FEATURES, VIEW_FEATURES,
    USER_BY_SCREEN_NAME_QUERYID, CREATE_ARTICLE_QUERYID,
)


def response_ok(response, graphql=False) -> bool:
    if response.status_code != 200:
        return False
    try:
        body = response.json()
    except (ValueError, TypeError):
        return False
    if not isinstance(body, dict) or not body or body.get("errors") or body.get("error"):
        return False
    if graphql:
        data = body.get("data")
        return isinstance(data, dict) and any(value is not None for value in data.values())
    return True


def tweet_visibility(result: dict) -> str:
    """Inspecte un résultat de tweet créé et renvoie '' s'il est visible
    normalement, sinon un court libellé du type de restriction.

    X ne signale PAS un tweet flagué spam via `errors` : le tweet est créé
    (rest_id présent) mais placé en visibilité réduite — invisible pour les
    autres comptes et sans notification pour les mentions. Il faut donc
    inspecter le typename du résultat.
    """
    if not isinstance(result, dict):
        return "unknown-result"
    if "tombstone" in result:
        return "tombstone"
    typename = result.get("__typename", "")
    if typename and typename != "Tweet":
        return typename  # ex. "TweetWithVisibilityResults"
    return ""


def _created_tweet_result(response) -> tuple[str, str]:
    """Extrait (rest_id, visibilité) d'une réponse CreateTweet. ('','') si introuvable."""
    try:
        result = response.json()["data"]["create_tweet"]["tweet_results"]["result"]
        return result.get("rest_id", ""), tweet_visibility(result)
    except Exception:
        return "", ""


def quote_tweet(session: XSession, tweet_text: str, mentions: str,
                mentions_first: bool = False,
                media_ids: list | None = None) -> tuple[bool, str, str]:
    """Poste un tweet contenant des @mentions.

    Renvoie (ok, rest_id, visibilité) — `visibilité` == '' si le tweet semble
    visible normalement, sinon le type de restriction détecté (le compte est
    alors probablement flagué/shadowbanné et la cible ne sera pas notifiée).
    """
    if mentions and mentions_first:
        text = f"{mentions}\n{tweet_text}"
    elif mentions:
        text = f"{tweet_text}\n{mentions}"
    else:
        text = tweet_text
    entities = ([{"media_id": m, "tagged_users": []} for m in media_ids]
                if media_ids else [])
    url = "https://x.com/i/api/graphql/MtyT_TbO2PpwaFHNPK2qoQ/CreateTweet"
    payload = {
        "variables": {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": entities, "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "disallowed_reply_options": None,
        },
        "features": TWEET_FEATURES,
        "queryId": "MtyT_TbO2PpwaFHNPK2qoQ",
    }
    r = session.post(url, payload, "https://x.com/compose/post")
    if response_ok(r, graphql=True):
        rest_id, visibility = _created_tweet_result(r)
        if rest_id:
            return True, rest_id, visibility
    return False, "", ""


def retweet(session: XSession, tweet_id: str) -> bool:
    url = "https://x.com/i/api/graphql/LFho5rIi4xcKO90p9jwG7A/CreateRetweet"
    payload = {
        "variables": {"tweet_id": tweet_id, "dark_request": False},
        "queryId": "LFho5rIi4xcKO90p9jwG7A",
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def like(session: XSession, tweet_id: str) -> bool:
    url = "https://x.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet"
    payload = {
        "variables": {"tweet_id": tweet_id},
        "queryId": "lI07N6Otwv1PhnEgXILM7A",
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def reply(session: XSession, tweet_id: str, reply_text: str,
          media_ids: list | None = None) -> tuple[bool, str, str]:
    """Renvoie (ok, rest_id, visibilité) — voir quote_tweet pour `visibilité`."""
    entities = ([{"media_id": m, "tagged_users": []} for m in media_ids]
                if media_ids else [])
    url = "https://x.com/i/api/graphql/MtyT_TbO2PpwaFHNPK2qoQ/CreateTweet"
    payload = {
        "variables": {
            "tweet_text": reply_text,
            "reply": {
                "in_reply_to_tweet_id": tweet_id,
                "exclude_reply_user_ids": [],
            },
            "dark_request": False,
            "media": {"media_entities": entities, "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "disallowed_reply_options": None,
        },
        "features": TWEET_FEATURES,
        "queryId": "MtyT_TbO2PpwaFHNPK2qoQ",
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    if response_ok(r, graphql=True):
        rest_id, visibility = _created_tweet_result(r)
        if rest_id:
            return True, rest_id, visibility
    return False, "", ""


def view_tweet(session: XSession, tweet_id: str) -> bool:
    url = "https://x.com/i/api/graphql/0hWvDhmW8YQ-S_ib3azIrw/TweetResultByRestId"
    params = {
        "variables": json.dumps({
            "tweetId": tweet_id,
            "withCommunity": False,
            "includePromotedContent": False,
            "withVoice": False,
        }),
        "features": json.dumps(VIEW_FEATURES),
    }
    r = session.get(url, params, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def bookmark(session: XSession, tweet_id: str) -> bool:
    url = "https://x.com/i/api/graphql/aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark"
    payload = {
        "variables": {"tweet_id": tweet_id},
        "queryId": "aoDbu3RHznuiSkQ9aNM67Q",
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def follow(session: XSession, screen_name: str) -> bool:
    url = "https://x.com/i/api/1.1/friendships/create.json"
    data = {
        "include_profile_interstitial_type": "1",
        "include_blocking": "1",
        "include_blocked_by": "1",
        "include_followed_by": "1",
        "include_want_retweets": "1",
        "include_mute_edge": "1",
        "include_can_dm": "1",
        "include_can_media_tag": "1",
        "include_ext_is_blue_verified": "1",
        "skip_status": "1",
        "screen_name": screen_name,
    }
    r = session.post_form(url, data, f"https://x.com/{screen_name}")
    return response_ok(r)


def update_profile_picture(session: XSession, image_path: str) -> bool:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # 1. Upload l'image — renvoie un media_id
    up = session.post_form(
        "https://upload.x.com/i/media/upload.json",
        {"media_data": b64},
        "https://x.com/settings/profile",
    )
    if up.status_code != 200:
        return False
    try:
        media_id = up.json().get("media_id_string")
    except Exception:
        return False
    if not media_id:
        return False

    # 2. Applique le media_id comme photo de profil
    r = session.post_form(
        "https://x.com/i/api/1.1/account/update_profile_image.json",
        {
            "media_id": media_id,
            "include_profile_interstitial_type": "1",
            "skip_status": "1",
        },
        "https://x.com/settings/profile",
    )
    return response_ok(r)


def update_profile(session: XSession, name: str = "", bio: str = "") -> bool:
    data = {
        "include_profile_interstitial_type": "1",
        "skip_status": "1",
    }
    if name:
        data["name"] = name
    if bio:
        data["description"] = bio

    r = session.post_form(
        "https://x.com/i/api/1.1/account/update_profile.json",
        data,
        "https://x.com/settings/profile",
    )
    return response_ok(r)


# ── Lookup utilisateur (UserByScreenName) ─────────────────────────────────────

def _lookup_user(session: XSession, screen_name: str) -> tuple[dict | None, str]:
    """Appelle UserByScreenName. Renvoie (result, '') ou (None, erreur)."""
    qid = USER_BY_SCREEN_NAME_QUERYID
    if not qid:
        return None, "queryId manquant"
    url = f"https://x.com/i/api/graphql/{qid}/UserByScreenName"
    params = {
        "variables": json.dumps({
            "screen_name": screen_name,
            "withSafetyModeUserFields": True,
        }),
        "features": json.dumps({
            "hidden_profile_likes_enabled": True,
            "hidden_profile_subscriptions_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "subscriptions_verification_info_is_identity_verified_enabled": True,
            "subscriptions_verification_info_verified_since_enabled": True,
            "highlights_tweets_tab_ui_enabled": True,
            "responsive_web_twitter_article_notes_tab_enabled": True,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
        }),
    }
    try:
        r = session.get(url, params, f"https://x.com/{screen_name}")
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} (queryId ?)"
        result = r.json()["data"]["user"]["result"]
        if not isinstance(result, dict):
            return None, "unexpected payload"
        return result, ""
    except Exception as e:
        return None, str(e)


def resolve_user_id(session: XSession, screen_name: str) -> tuple[str, str]:
    """Résout un @username en user_id numérique. Renvoie (user_id, erreur)."""
    result, err = _lookup_user(session, screen_name)
    if err:
        return "", err
    uid = result.get("rest_id", "") or result.get("id", "")
    return (str(uid), "") if uid else ("", "user_id introuvable")


def check_premium(session: XSession, screen_name: str) -> dict:
    """Lit le statut Premium/Blue du compte via UserByScreenName.

    Renvoie {ok, premium, verified_type, error}. `premium` = a un badge Blue
    (Premium). Les X Articles requièrent en principe Premium+ (le tier le plus
    haut), non distinguable de façon fiable ici — d'où l'avertissement.
    """
    result, err = _lookup_user(session, screen_name)
    if err:
        return {"ok": False, "premium": False, "verified_type": "", "error": err}
    premium = bool(result.get("is_blue_verified"))
    vtype = result.get("legacy", {}).get("verified_type") or result.get("verified_type") or ""
    return {"ok": True, "premium": premium, "verified_type": vtype, "error": ""}


# ── Messages privés (DM) ──────────────────────────────────────────────────────

def send_dm(session: XSession, recipient_id: str, text: str) -> bool:
    """Envoie un message privé à un user_id. Chez un destinataire inconnu,
    le message arrive en « demande de message » — qui déclenche une
    notification, contrairement aux mentions filtrées des comptes flagués.
    """
    data = {
        "request_id": str(uuid.uuid4()),
        "recipient_id": str(recipient_id),
        "text": text,
        "cards_platform": "Web-12",
        "include_cards": "0",
        "include_quote_count": "false",
        "dm_users": "false",
    }
    r = session.post_form(
        "https://x.com/i/api/1.1/dm/new2.json",
        data,
        f"https://x.com/messages/{recipient_id}",
    )
    return response_ok(r)


def publish_article(session: XSession, article: dict) -> tuple[bool, str]:
    """Publie un X Article.

    ⚠️ La mutation CreateArticle est versionnée : renseigne CREATE_ARTICLE_QUERYID
    (et adapte le payload) depuis une vraie publication capturée en DevTools.
    `article` = {title, subtitle?, body, cover_media_id?}.
    """
    qid = CREATE_ARTICLE_QUERYID
    if not qid:
        return False, "CREATE_ARTICLE_QUERYID non renseigné (voir constants.py)"

    # Structure de départ — À AJUSTER selon le payload réel capturé.
    payload = {
        "variables": {
            "title": article.get("title", ""),
            "cover_media_id": article.get("cover_media_id"),
            # X stocke le corps sous forme de document riche (JSON). En première
            # approche on envoie le texte ; remplace par la vraie structure.
            "content_state": article.get("body", ""),
        },
        "queryId": qid,
    }
    url = f"https://x.com/i/api/graphql/{qid}/CreateArticle"
    try:
        r = session.post(url, payload, "https://x.com/compose/article")
        if r.status_code == 200 and "errors" not in (r.json() or {}):
            data = r.json().get("data", {})
            # le chemin exact du rest_id dépend de la réponse réelle
            rid = json.dumps(data)[:64]
            return True, rid
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)
