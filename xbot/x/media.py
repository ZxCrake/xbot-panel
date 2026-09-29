"""Image upload to X (media/upload.json INIT/APPEND/FINALIZE).

Probed live 2026-09-26 against upload.x.com with the standard XSession
headers (cookie + ct0 + bearer). APPEND uses base64 media_data form fields —
avoids multipart entirely and matches what the web client accepts. Returned
media_id attaches to CreateTweet via media_entities.
"""
import base64

UPLOAD_URL = "https://upload.x.com/1.1/media/upload.json"
COMPOSE_REFERER = "https://x.com/compose/post"

# X photo limit is 5 MB; keep margin for base64 + safety.
MAX_IMAGE_BYTES = 4_500_000


def upload_image(session, data: bytes, mime: str = "image/jpeg") -> str:
    """Upload one image, return media_id_string ('' on failure)."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        return ""
    r = session.post_form(UPLOAD_URL, {
        "command": "INIT",
        "total_bytes": str(len(data)),
        "media_type": mime,
        "media_category": "tweet_image",
    }, COMPOSE_REFERER)
    try:
        media_id = r.json().get("media_id_string", "")
    except Exception:
        return ""
    if not media_id:
        return ""
    r = session.post_form(UPLOAD_URL, {
        "command": "APPEND",
        "media_id": media_id,
        "segment_index": "0",
        "media_data": base64.b64encode(data).decode(),
    }, COMPOSE_REFERER)
    if r.status_code not in (200, 204):
        return ""
    r = session.post_form(UPLOAD_URL, {
        "command": "FINALIZE",
        "media_id": media_id,
    }, COMPOSE_REFERER)
    try:
        ok = r.status_code in (200, 201) and str(
            r.json().get("media_id_string", "")) == media_id
    except Exception:
        return ""
    return media_id if ok else ""
