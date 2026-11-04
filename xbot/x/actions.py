import json
import os
import base64
import uuid
from . import articles, query_ids
from .session import XSession
from .constants import ARTICLE_FEATURES, TWEET_FEATURES, VIEW_FEATURES


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
    qid = query_ids.get("CreateTweet")
    if not qid:
        return False, "", ""
    if mentions and mentions_first:
        text = f"{mentions}\n{tweet_text}"
    elif mentions:
        text = f"{tweet_text}\n{mentions}"
    else:
        text = tweet_text
    entities = ([{"media_id": m, "tagged_users": []} for m in media_ids]
                if media_ids else [])
    url = f"https://x.com/i/api/graphql/{qid}/CreateTweet"
    payload = {
        "variables": {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": entities, "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "disallowed_reply_options": None,
        },
        "features": TWEET_FEATURES,
        "queryId": qid,
    }
    r = session.post(url, payload, "https://x.com/compose/post")
    if response_ok(r, graphql=True):
        rest_id, visibility = _created_tweet_result(r)
        if rest_id:
            return True, rest_id, visibility
    return False, "", ""


def retweet(session: XSession, tweet_id: str) -> bool:
    qid = query_ids.get("CreateRetweet")
    if not qid:
        return False
    url = f"https://x.com/i/api/graphql/{qid}/CreateRetweet"
    payload = {
        "variables": {"tweet_id": tweet_id, "dark_request": False},
        "queryId": qid,
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def like(session: XSession, tweet_id: str) -> bool:
    qid = query_ids.get("FavoriteTweet")
    if not qid:
        return False
    url = f"https://x.com/i/api/graphql/{qid}/FavoriteTweet"
    payload = {
        "variables": {"tweet_id": tweet_id},
        "queryId": qid,
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    return response_ok(r, graphql=True)


def reply(session: XSession, tweet_id: str, reply_text: str,
          media_ids: list | None = None) -> tuple[bool, str, str]:
    """Renvoie (ok, rest_id, visibilité) — voir quote_tweet pour `visibilité`."""
    qid = query_ids.get("CreateTweet")
    if not qid:
        return False, "", ""
    entities = ([{"media_id": m, "tagged_users": []} for m in media_ids]
                if media_ids else [])
    url = f"https://x.com/i/api/graphql/{qid}/CreateTweet"
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
        "queryId": qid,
    }
    r = session.post(url, payload, f"https://x.com/i/status/{tweet_id}")
    if response_ok(r, graphql=True):
        rest_id, visibility = _created_tweet_result(r)
        if rest_id:
            return True, rest_id, visibility
    return False, "", ""


def view_tweet(session: XSession, tweet_id: str) -> bool:
    qid = query_ids.get("TweetResultByRestId")
    if not qid:
        return False
    url = f"https://x.com/i/api/graphql/{qid}/TweetResultByRestId"
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
    qid = query_ids.get("CreateBookmark")
    if not qid:
        return False
    url = f"https://x.com/i/api/graphql/{qid}/CreateBookmark"
    payload = {
        "variables": {"tweet_id": tweet_id},
        "queryId": qid,
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


def _read_gmail_code(email: str, gmail_password: str) -> str:
    """Dernier code à 6 chiffres de la boîte Gmail (via tools/gmail_create.mjs)."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(root, "tools", "gmail_create.mjs")
    try:
        out = subprocess.run(
            ["node", script, "code", email, gmail_password],
            capture_output=True, text=True, timeout=120, cwd=root)
    except Exception:
        return ""
    for line in reversed((out.stdout or "").splitlines()):
        line = line.strip()
        if line.isdigit() and len(line) in (6, 8):
            return line
    return ""


def _flow_step(subtasks):
    """Prochaine entrée attendue du flow add_email : (subtask_id, clé, ) ou ('','')."""
    for st in subtasks or []:
        if not isinstance(st, dict):
            continue
        sid = st.get("subtask_id", "")
        for key in ("enter_email", "enter_code", "enter_password"):
            if key in st:
                return sid, key
    return "", ""


def _change_email_flow(session, email, password, gmail_password, get_code,
                      referer="https://x.com/settings/profile", max_steps=8):
    """Flow officiel X : POST /i/api/1.1/onboarding/task.json?flow_name=add_email.

    Étapes : enter_email → enter_code (code Gmail) → enter_password → fin.
    Renvoie True quand le flow s'achève sans sous-écran d'entrée restant.
    """
    url = "https://x.com/i/api/1.1/onboarding/task.json?flow_name=add_email"
    payload = {"input_data": {"flow_name": "add_email"}}
    for _ in range(max_steps):
        r = session.post(url, payload, referer)
        if r.status_code != 200:
            return False
        try:
            body = r.json()
        except Exception:
            return False
        if not isinstance(body, dict) or body.get("errors"):
            return False
        data = body.get("data")
        if not isinstance(data, dict):
            return False
        token = data.get("flow_token", "")
        sid, key = _flow_step(data.get("subtasks", []))
        if not key:
            return bool(token)  # plus d'entrée attendue → flow terminé
        if key == "enter_email":
            value = {"email": email}
        elif key == "enter_password":
            if not password:
                return False  # le flow exige le mot de passe X (champ n°2)
            value = {"password": password}
        else:  # enter_code
            code = (get_code or _read_gmail_code)(email, gmail_password)
            if not code:
                return False
            value = {"code": str(code).strip()}
        payload = {"input_data": {
            "flow_token": token,
            "subtask_inputs": [{"subtask_id": sid, key: value}],
        }}
    return False


def _change_email_graphql(session, email, password,
                          referer="https://x.com/settings/profile"):
    """Repli legacy : mutation GraphQL UpdateProfileEmail (404 sur le web actuel)."""
    qid = query_ids.get("UpdateProfileEmail")
    if not qid:
        return False
    variables = {"email": email}
    if password:
        variables["password"] = password
    url = f"https://x.com/i/api/graphql/{qid}/UpdateProfileEmail"
    payload = {"variables": variables, "queryId": qid}
    r = session.post(url, payload, referer)
    return response_ok(r, graphql=True)


def change_email(session: XSession, email: str, password: str = "",
                 gmail_password: str = "", get_code=None) -> bool:
    """Nouvelle adresse e-mail du compte X.

    `email` = la nouvelle adresse (Gmail créé par tools/gmail_create.mjs,
    second champ de la ligne = mot de passe Gmail, voir `gmail_password`) ;
    `password` = mot de passe du compte X (champ n°2 de accounts.txt) ;
    `get_code` = fonction optionnelle (email, mdp) -> code pour lire la boîte.
    Mécanisme principal : le flow onboarding « add_email » ; repli : l'ancienne
    mutation GraphQL. Renvoie True en cas d'ack.
    """
    if _change_email_flow(session, email, password, gmail_password, get_code):
        return True
    return _change_email_graphql(session, email, password)


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
    qid = query_ids.get("UserByScreenName")
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


# ── X Articles (draft → titre → contenu → cover → publication) ───────────────

_ARTICLE_COMPOSE = "https://x.com/compose/articles"


def _article_post(session: XSession, operation: str, variables: dict,
                  referer: str) -> tuple[dict | None, str]:
    """POST one ArticleEntity* mutation. Returns (json, error)."""
    qid = query_ids.get(operation)
    if not qid:
        return None, f"queryId manquant pour {operation} (voir constants.py)"
    url = f"https://x.com/i/api/graphql/{qid}/{operation}"
    payload = {"variables": variables, "features": ARTICLE_FEATURES, "queryId": qid}
    try:
        r = session.post(url, payload, referer)
    except Exception as e:
        return None, f"{operation}: {e}"
    if not response_ok(r, graphql=True):
        detail = ""
        try:
            detail = str((r.json() or {}).get("errors") or "")[:180]
        except Exception:
            pass
        return None, f"{operation}: HTTP {r.status_code}" + (
            f" — {detail}" if detail else "")
    try:
        return r.json(), ""
    except Exception as e:
        return None, f"{operation}: réponse illisible ({e})"


def _article_rest_id(data: dict | None) -> str:
    """Extract the article rest_id from any ArticleEntity* response."""
    for value in ((data or {}).get("data") or {}).values():
        if not isinstance(value, dict):
            continue
        result = (value.get("article_entity_results") or {}).get("result", value)
        if not isinstance(result, dict):
            continue
        if result.get("rest_id"):
            return str(result["rest_id"])
        if result.get("id"):
            try:
                decoded = base64.b64decode(str(result["id"]) + "==").decode()
                return decoded.split(":", 1)[1]
            except Exception:
                pass
    return ""


def _published_tweet_id(data: dict | None) -> str:
    try:
        return str(data["data"]["articleentity_publish"]["article_entity_results"]
                   ["result"]["metadata"]["tweet_results"]["result"]["rest_id"])
    except (KeyError, TypeError):
        return ""


def publish_article(session: XSession, article: dict) -> tuple[bool, str]:
    """Publie un X Article via le flux web (5 mutations).

    `article` = {title, subtitle?, body (HTML), cover_media_id?}.
    Renvoie (ok, tweet_id | message d'erreur).
    """
    title = str(article.get("title", "") or "").strip()
    if not title:
        return False, "article title is empty"
    content_state = articles.content_state_from_html(
        article.get("body", ""), article.get("subtitle", ""))

    draft, err = _article_post(
        session, "ArticleEntityDraftCreate",
        {"content_state": {"blocks": [], "entity_map": []}, "title": title},
        _ARTICLE_COMPOSE)
    if err:
        return False, err
    article_id = _article_rest_id(draft)
    if not article_id:
        return False, "article id introuvable dans la réponse de création"
    edit_url = f"{_ARTICLE_COMPOSE}/edit/{article_id}"

    for operation, variables in (
        ("ArticleEntityUpdateTitle",
         {"articleEntityId": article_id, "title": title}),
        ("ArticleEntityUpdateContent",
         {"content_state": content_state, "article_entity": article_id}),
    ):
        _, err = _article_post(session, operation, variables, edit_url)
        if err:
            return False, f"{err} (article {article_id})"

    cover = article.get("cover_media_id")
    if cover:
        _, err = _article_post(
            session, "ArticleEntityUpdateCoverMedia",
            {"articleEntityId": article_id,
             "coverMedia": {"media_id": str(cover),
                            "media_category": "DraftTweetImage"}},
            edit_url)
        if err:
            return False, f"{err} (article {article_id})"

    published, err = _article_post(
        session, "ArticleEntityPublish",
        {"articleEntityId": article_id, "visibilitySetting": "Public"},
        edit_url)
    if err:
        return False, f"{err} (article {article_id})"
    return True, _published_tweet_id(published) or article_id
