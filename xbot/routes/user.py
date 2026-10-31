import os
import re
import json

from flask import Blueprint, request, jsonify

from ..auth import login_required
from ..audit import log_action
from ..context import (current_dir, current_user, farm_busy, get_farm,
                       get_runner, read_config, write_config)
from ..runner import ACTION_NAMES
from ..security import validate_config
from ..x.session import XSession
from ..x import scraper
from ..security import limiter
from .. import settings
from ..files import safe_file, profile_path
from ..x import query_ids
from ..proxies import resolve_for_account, resolve_for_fetch

bp = Blueprint("user", __name__)


@bp.route("/api/config", methods=["GET", "POST"])
@login_required
def config():
    if request.method == "POST":
        try:
            clean = validate_config(request.get_json(silent=True) or {})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        write_config(clean)
        return jsonify({"ok": True})
    return jsonify(read_config())


@bp.route("/api/file/<name>", methods=["GET", "POST"])
@login_required
def file(name):
    if name not in settings.EDITABLE_FILES:
        return jsonify({"error": "file not allowed"}), 400
    path = safe_file(current_dir(), name)
    if request.method == "POST":
        content = (request.get_json(silent=True) or {}).get("content", "")
        if not isinstance(content, str):
            return jsonify({"error": "content must be a string"}), 400
        if len(content.encode("utf-8")) > settings.MAX_FILE_BYTES:
            return jsonify({"error": "file too large"}), 413
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log_action("file.save", username=current_user(), detail=name)
        return jsonify({"ok": True})
    content = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    return jsonify({"content": content})


@bp.route("/api/upload-pfp", methods=["POST"])
@login_required
def upload_pfp():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    cfg = read_config()
    pfp_name = cfg.get("pfp_image", "pfp.jpg")
    try:
        path = profile_path(current_dir(), pfp_name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    content = f.read(settings.MAX_PFP_BYTES + 1)
    if len(content) > settings.MAX_PFP_BYTES:
        return jsonify({"error": "image too large"}), 413
    if not content:
        return jsonify({"error": "empty image"}), 400
    with open(path, "wb") as target:
        target.write(content)
    log_action("pfp.upload", username=current_user(), detail=pfp_name)
    return jsonify({"ok": True, "saved": pfp_name})


@bp.route("/api/run", methods=["POST"])
@login_required
def run():
    data = request.get_json(silent=True) or {}
    try:
        action_mode = int(data.get("action_mode", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid action"}), 400
    if action_mode not in ACTION_NAMES:
        return jsonify({"error": "invalid action"}), 400
    if farm_busy():
        return jsonify({"error": "Farm is running — stop it before launching a manual job "
                         "(avoids account-level rate doubling)"}), 409
    if "config" in data:
        try:
            write_config(validate_config(data["config"]))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    err = get_runner().start(action_mode, read_config(), current_dir())
    if err:
        return jsonify({"error": err}), 400
    log_action("job.start", username=current_user(), detail=ACTION_NAMES[action_mode])
    return jsonify({"ok": True})


@bp.route("/api/stop", methods=["POST"])
@login_required
def stop():
    err = get_runner().stop()
    if err:
        return jsonify({"error": err}), 400
    log_action("job.stop", username=current_user())
    return jsonify({"ok": True})


@bp.route("/api/status")
@login_required
@limiter.exempt   # polled every ~1.5s by the dashboard; not a sensitive endpoint
def status():
    return jsonify(get_runner().status())


# ── Farm (réchauffement autonome des comptes) ────────────────────────────────

@bp.route("/api/farm/start", methods=["POST"])
@login_required
def farm_start():
    if get_runner().is_running():
        return jsonify({"error": "A manual job is running — stop it before starting the farm "
                         "(avoids account-level rate doubling)"}), 409
    data = request.get_json(silent=True) or {}
    detail = f"{data.get('duration_days')}d/{list((data.get('actions') or {}).values())}"
    err = get_farm().start(data)
    if err:
        return jsonify({"error": err}), 400
    log_action("farm.start", username=current_user(), detail=detail)
    return jsonify({"ok": True})


@bp.route("/api/farm/stop", methods=["POST"])
@login_required
def farm_stop():
    err = get_farm().stop()
    if err:
        return jsonify({"error": err}), 400
    log_action("farm.stop", username=current_user())
    return jsonify({"ok": True})


@bp.route("/api/farm/status")
@login_required
@limiter.exempt
def farm_status():
    return jsonify(get_farm().status())


@bp.route("/api/farm/scores")
@login_required
@limiter.exempt
def farm_scores():
    return jsonify(get_farm().scores())


def _config_proxy() -> str:
    """Proxy HTTP pour les récupérations publiques/anonymes (contourner le
    rate-limit par IP de la syndication / des images). En mode rotatif,
    volontairement SANS session épinglée : IP fraîche à chaque requête."""
    return resolve_for_fetch(read_config())


@bp.route("/api/farm/generate", methods=["POST"])
@login_required
def farm_generate():
    """Génère du contenu de vie — renvoyé au navigateur pour revue avant
    enregistrement. Seule écriture : le cache 24 h des IDs viraux (anti
    rate-limit syndication) ; le contenu lui-même reste à confirmer."""
    from .. import farm_content
    data = request.get_json(silent=True) or {}
    channel = data.get("channel", "")
    lang = data.get("lang", "fr")
    if lang not in ("fr", "en"):
        return jsonify({"error": "lang must be 'fr' or 'en'"}), 400
    if channel == "media":
        # Binaire : écriture directe dans la banque média (pas de revue texte).
        try:
            count = int(data.get("count", 10))
            if not 1 <= count <= 20:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"error": "count must be between 1 and 20"}), 400
        added = farm_content.fetch_stock_images(
            current_dir(), count=count, proxy=_config_proxy())
        total = len(farm_content.media_bank(current_dir()))
        log_action("farm.generate", username=current_user(),
                   detail=f"media:+{added}/{total}")
        if added == 0 and total == 0:
            return jsonify({"error": "Remote fetch unavailable right now "
                                     "— try again later"}), 502
        return jsonify({"ok": True, "added": added, "total": total})
    try:
        lines = farm_content.generate(channel, lang=lang,
                                      proxy=_config_proxy() if channel == "tweet_ids" else "")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if channel == "tweet_ids":
        if lines:
            farm_content.cache_write(current_dir(), lines)
        else:
            lines = farm_content.cache_read(current_dir())
            if lines:
                log_action("farm.generate", username=current_user(), detail="tweet_ids:cache")
                return jsonify({"ok": True, "lines": lines, "from_cache": True})
            if farm_content.LAST_STATUS.get("saw_429"):
                return jsonify({"error": "Fetch temporarily rate-limited by X. "
                                         "Retry in a few minutes, or set a proxy "
                                         "in the configuration."}), 502
            return jsonify({"error": "Remote fetch unavailable right now "
                                     "— try again later"}), 502
    log_action("farm.generate", username=current_user(), detail=f"{channel}:{lang}")
    return jsonify({"ok": True, "lines": lines})


IMPORT_FIELDS = {"USER", "PASS", "EMAIL", "EMAILPWD", "CT0", "AUTH_TOKEN", "2FA_BACKUP_CODE"}


@bp.route("/api/proxy/rotate-sessions", methods=["POST"])
@login_required
def rotate_proxy_sessions():
    """Bumpe l'epoch des sessions épinglées : chaque compte reçoit un nouvel
    identifiant de session → nouvelles IP de sortie sur la gateway rotative.
    À utiliser quand les IP courantes sont grillées par X."""
    cfg = read_config()
    if str(cfg.get("proxy_mode", "static")) != "rotating":
        return jsonify({"error": "proxy_mode is not 'rotating'"}), 400
    try:
        epoch = int(cfg.get("proxy_session_epoch", 0)) + 1
    except (TypeError, ValueError):
        epoch = 1
    write_config({"proxy_session_epoch": epoch})
    log_action("proxy.rotate", username=current_user(), detail=f"epoch={epoch}")
    return jsonify({"ok": True, "epoch": epoch})


IMPORT_FIELDS = {"USER", "PASS", "EMAIL", "EMAILPWD", "CT0", "AUTH_TOKEN", "2FA_BACKUP_CODE"}


@bp.route("/api/import-accounts", methods=["POST"])
@login_required
def import_accounts():
    data = request.get_json(silent=True) or {}
    fields = data.get("fields", [])
    sep = data.get("separator") or ":"
    mode = data.get("mode", "append")
    content = data.get("content", "")
    if not isinstance(sep, str) or not 1 <= len(sep) <= 3:
        return jsonify({"error": "separator must contain 1 to 3 characters"}), 400
    if mode not in ("append", "replace"):
        return jsonify({"error": "mode must be append or replace"}), 400

    if not isinstance(fields, list) or not fields:
        return jsonify({"error": "no field layout chosen"}), 400
    if any(not isinstance(f, str) or f not in IMPORT_FIELDS for f in fields):
        return jsonify({"error": "unknown field in layout"}), 400
    if len(set(fields)) != len(fields):
        return jsonify({"error": "duplicate field in layout"}), 400
    if "AUTH_TOKEN" not in fields:
        return jsonify({"error": "AUTH_TOKEN is required"}), 400
    if not isinstance(content, str) or not content.strip():
        return jsonify({"error": "no content"}), 400
    if len(content.encode("utf-8")) > settings.MAX_FILE_BYTES:
        return jsonify({"error": "file too large"}), 413

    idx = {name: i for i, name in enumerate(fields)}
    out, errors = [], 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(sep)
        if len(parts) != len(fields):
            errors += 1
            continue
        token = parts[idx["AUTH_TOKEN"]].strip()
        if not token:
            errors += 1
            continue
        user = (parts[idx["USER"]].strip() if "USER" in idx else "") or f"acct{len(out) + 1}"
        # Canonical internal format: username:[extras…]:auth_token — le runner
        # lit [0] et [-1] ; les champs intermédiaires choisis (PASS, EMAIL,
        # 2FA_BACKUP_CODE…) sont conservés pour l'action 14 (change e-mail
        # exige le mot de passe X en champ n°2) au lieu d'être jetés.
        extras = [parts[idx[f]].strip() for f in fields
                  if f not in ("USER", "AUTH_TOKEN") and idx[f] < len(parts)]
        out.append(":".join([user] + extras + [token]))

    path = safe_file(current_dir(), "accounts.txt")
    existing = []
    if mode == "append" and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = [ln.strip() for ln in f if ln.strip()]
    combined = "\n".join(existing + out) + ("\n" if (existing or out) else "")
    if len(combined.encode("utf-8")) > settings.MAX_FILE_BYTES:
        return jsonify({"error": "combined accounts file too large"}), 413
    if len(existing) + len(out) > settings.MAX_ACCOUNTS_PER_JOB:
        return jsonify({"error": "too many accounts"}), 400
    with open(path, "w", encoding="utf-8") as f:
        f.write(combined)

    log_action("accounts.import", username=current_user(),
               detail=f"{len(out)} imported, {errors} skipped, layout={'/'.join(fields)}")
    return jsonify({"ok": True, "imported": len(out), "errors": errors, "total": len(existing) + len(out)})


@bp.route("/api/scrape", methods=["POST"])
@login_required
@limiter.limit("2 per minute")
def scrape():
    data = request.get_json(silent=True) or {}
    tweet_id = str(data.get("tweet_id", "")).strip()
    # Accept a full tweet URL (…/status/<id>) as well as a bare ID.
    m = re.search(r"status(?:es)?/(\d+)", tweet_id)
    if m:
        tweet_id = m.group(1)
    targets = data.get("targets", [])
    if not tweet_id.isdigit():
        return jsonify({"error": "invalid tweet link or ID"}), 400
    if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets):
        return jsonify({"error": "targets must be a list of names"}), 400
    targets = list(dict.fromkeys(t for t in targets if t in scraper.SCRAPERS))
    if not targets:
        return jsonify({"error": "select at least one of: likes, retweets, replies, quotes"}), 400
    try:
        max_results = int(data.get("max_results", 500))
        if not 1 <= max_results <= 5000:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "max_results must be between 1 and 5000"}), 400
    scrape_ids = {"likes": query_ids.get("Favoriters"), "retweets": query_ids.get("Retweeters"),
                  "replies": query_ids.get("TweetDetail"), "quotes": query_ids.get("SearchTimeline")}
    if any(not scrape_ids[t] for t in targets):
        return jsonify({"error": "Scraping is unavailable: the X integration is incomplete"}), 503

    # Use the first account in accounts.txt as the scraping identity.
    acc_path = safe_file(current_dir(), "accounts.txt")
    accounts = []
    if os.path.exists(acc_path):
        with open(acc_path, encoding="utf-8") as f:
            accounts = [ln.strip() for ln in f if ln.strip()]
    if not accounts:
        return jsonify({"error": "No X accounts imported — at least one is required for extraction"}), 400

    cfg = read_config()
    acc = accounts[0]
    with XSession(auth_token=acc.split(":")[-1],
                  proxy=resolve_for_account(cfg, 0)) as sess:
        if not sess.authenticate():
            return jsonify({"error": "scraper account failed to authenticate"}), 400
        results = {}
        for t in targets:
            try:
                results[t] = scraper.SCRAPERS[t](sess, tweet_id, max_results)
            except Exception:
                results[t] = {"error": "Scraper request failed", "items": []}

    log_action("scrape", username=current_user(), detail=f"{tweet_id} [{','.join(targets)}]")
    return jsonify({"tweet_id": tweet_id, "results": results})


@bp.route("/api/articles", methods=["GET", "POST"])
@login_required
def articles():
    path = safe_file(current_dir(), "articles.json")
    if request.method == "POST":
        raw = (request.get_json(silent=True) or {}).get("articles", [])
        if not isinstance(raw, list):
            return jsonify({"error": "articles must be a list"}), 400
        clean = []
        for a in raw[:200]:
            if not isinstance(a, dict):
                continue
            title = str(a.get("title", ""))[:300]
            body = str(a.get("body", ""))
            if len(body.encode("utf-8")) > settings.MAX_FILE_BYTES:
                return jsonify({"error": f"article “{title}” body too large"}), 413
            clean.append({
                "title": title,
                "subtitle": str(a.get("subtitle", ""))[:500],
                "body": body,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        log_action("articles.save", username=current_user(), detail=f"{len(clean)} articles")
        return jsonify({"ok": True, "count": len(clean)})

    arts = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                arts = json.load(f)
        except (json.JSONDecodeError, OSError):
            arts = []
    return jsonify({"articles": arts if isinstance(arts, list) else []})
