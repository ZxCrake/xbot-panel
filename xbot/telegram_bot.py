"""Bot Telegram d'administration du panneau.

Long-polling via urllib (aucune dépendance externe). Le thread démarre depuis
create_app() dès que TELEGRAM_BOT_TOKEN est défini.

Sécurité
────────
Le bot ne répond qu'à UN compte. Au premier contact dont le @username
correspond à TELEGRAM_ADMIN (défaut `Nx0xb`), son ID numérique est épinglé
dans DATA_ROOT/telegram.json : ensuite seul cet ID est accepté, même si le
@username change de main. TELEGRAM_ADMIN_ID peut fixer l'ID d'emblée.

Toutes les actions passent par les mêmes objets que le panneau web
(`context.runners` / `context.farms`), donc un job lancé depuis Telegram est
visible dans l'interface et inversement.
"""
import datetime as dt
import html
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request

from . import settings
from .db import session, User, AuditLog
from . import context
from .files import safe_file, workspace_path
from .runner import ACTION_NAMES, BotRunner
from .farm import FarmRunner

log = logging.getLogger("xbot.telegram")

API_URL = "https://api.telegram.org/bot{token}/{method}"
MAX_TEXT = 4000          # marge sous la limite Telegram de 4096
POLL_TIMEOUT = 50        # long-polling (secondes)
AUDIT_INTERVAL = 15      # veille des connexions


# ── Client HTTP (injectable dans les tests) ──────────────────────────────────

class TelegramError(Exception):
    pass


class TelegramClient:
    def __init__(self, token: str, timeout: int = 60):
        self.token = token
        self.timeout = timeout

    def call(self, method: str, **payload):
        url = API_URL.format(token=self.token, method=method)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                raise TelegramError(f"HTTP {e.code}")
            raise TelegramError(body.get("description") or f"HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TelegramError(str(e))
        if not body.get("ok"):
            raise TelegramError(body.get("description") or "telegram error")
        return body.get("result")


# ── Autorisation ─────────────────────────────────────────────────────────────

def is_authorized(user_id: int, username: str, pinned_id: int | None,
                  admin_username: str) -> bool:
    """Seul le compte épinglé — ou, avant épinglage, le bon @username."""
    if pinned_id:
        return int(user_id) == int(pinned_id)
    return (username or "").lstrip("@").lower() == admin_username.lstrip("@").lower()


class AdminStore:
    """Épingle l'ID Telegram de l'administrateur (anti-usurpation de @username)."""

    def __init__(self, path: str):
        self.path = path

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)


# ── Accès données (hors contexte Flask) ──────────────────────────────────────

def _user(username: str) -> User | None:
    return session().query(User).filter_by(username=username).first()


def _users() -> list:
    return session().query(User).order_by(User.username).all()


def _user_dir(u: User) -> str:
    d = workspace_path(settings.USER_DATA_ROOT, u.workspace_key)
    os.makedirs(d, exist_ok=True)
    return d


def _config(u: User) -> dict:
    from .settings import DEFAULT_CONFIG
    cfg = dict(DEFAULT_CONFIG)
    path = safe_file(_user_dir(u), "config.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def _runner_for(u: User) -> BotRunner:
    key = u.workspace_key
    with context.runners_lock:
        if key not in context.runners:
            context.runners[key] = BotRunner(
                authorized=lambda: context.workspace_is_active(key))
        return context.runners[key]


def _farm_for(u: User) -> FarmRunner:
    key = u.workspace_key
    with context.runners_lock:
        if key not in context.farms:
            f = FarmRunner(base_dir=_user_dir(u),
                           authorized=lambda: context.workspace_is_active(key))
            f.maybe_resume()
            context.farms[key] = f
        return context.farms[key]


def _count_lines(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            return sum(1 for ln in f if ln.strip())
    except OSError:
        return 0


def _fmt_ts(value) -> str:
    """Horodatage lisible (UTC stocké en base, affiché en heure locale serveur)."""
    if not value:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone().strftime("%d/%m %H:%M:%S")


def _ago(value) -> str:
    if not value:
        return "jamais"
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    delta = dt.datetime.now(dt.timezone.utc) - value
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"il y a {secs} s"
    if secs < 3600:
        return f"il y a {secs // 60} min"
    if secs < 86400:
        return f"il y a {secs // 3600} h"
    return f"il y a {secs // 86400} j"


# ── Rendu des écrans (fonctions pures → testables) ───────────────────────────

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _counts() -> str:
    """Ligne d'état compacte réutilisée dans l'en-tête du menu."""
    try:
        users = _users()
    except Exception:          # base pas encore prête (tests, premier boot)
        return "👥 — · ▶️ — · 🌾 —"
    jobs = farms = 0
    for u in users:
        r = context.runners.get(u.workspace_key)
        f = context.farms.get(u.workspace_key)
        if r is not None and r.is_running():
            jobs += 1
        if f is not None and f.running:
            farms += 1
    return (f"👥 {len(users)} utilisateur(s) · ▶️ {jobs} job(s) · "
            f"🌾 {farms} ferme(s)")


def main_menu_text() -> str:
    return ("<b>🤖 Panneau X — administration</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{_counts()}\n"
            f"🌐 {esc(settings.ENV)} · 🗄 {esc(settings.DATABASE_URL.split('://')[0])}\n\n"
            "Choisis une section :")


def help_text() -> str:
    return ("<b>❓ Aide</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>/start</b> — menu principal\n"
            "<b>/status</b> — tableau de bord\n"
            "<b>/help</b> — cette aide\n\n"
            "Navigation : les boutons remplacent le message courant ; "
            "« ⬅️ Retour » remonte d'un niveau.\n\n"
            "<b>Ce que fait chaque section</b>\n"
            "• <b>Tableau de bord</b> — jobs et fermes en cours\n"
            "• <b>Utilisateurs</b> — comptes X, dernière connexion, état\n"
            "• <b>Lancer une action</b> — les 14 actions du panneau\n"
            "• <b>Ferme</b> — réchauffement autonome et scores\n"
            "• <b>Connexions</b> — qui s'est connecté, quand, depuis quelle IP\n"
            "• <b>Serveur</b> — environnement, base, uptime")


def main_menu_keyboard() -> dict:
    return {"inline_keyboard": [
        [{"text": "📊 Tableau de bord", "callback_data": "v:dash"}],
        [{"text": "👥 Utilisateurs", "callback_data": "v:users"}],
        [{"text": "▶️ Lancer une action", "callback_data": "v:run"}],
        [{"text": "🌾 Ferme", "callback_data": "v:farm"}],
        [{"text": "🔐 Connexions", "callback_data": "v:login"}],
        [{"text": "🖥 Serveur", "callback_data": "v:server"},
         {"text": "❓ Aide", "callback_data": "v:help"}],
    ]}


def dashboard_text() -> str:
    users = _users()
    lines = ["<b>📊 Tableau de bord</b>", ""]
    running_jobs, running_farms = [], []
    for u in users:
        r = context.runners.get(u.workspace_key)
        f = context.farms.get(u.workspace_key)
        if r and r.is_running():
            running_jobs.append(u.username)
        if f and f.running:
            running_farms.append(u.username)
    lines.append(f"Utilisateurs : <b>{len(users)}</b>")
    lines.append(f"Jobs en cours : <b>{len(running_jobs)}</b>"
                 + (f" — {esc(', '.join(running_jobs))}" if running_jobs else ""))
    lines.append(f"Fermes actives : <b>{len(running_farms)}</b>"
                 + (f" — {esc(', '.join(running_farms))}" if running_farms else ""))
    return "\n".join(lines)


USERS_HEADER = ("<b>👥 Utilisateurs</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "● actif · ○ inactif\n\n"
                "Choisis un compte :")


def run_header() -> str:
    return ("<b>▶️ Lancer une action</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Le job utilisera les fichiers déjà enregistrés dans le "
            "workspace du compte choisi.\n\n"
            "Choisis l'utilisateur :")


def farm_header() -> str:
    return ("<b>🌾 Ferme</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Réchauffement autonome des comptes.\n\n"
            "Choisis l'utilisateur :")


def users_keyboard(mode: str = "u") -> dict:
    """mode = 'u' (fiche), 'a' (actions) ou 'f' (ferme) selon la section."""
    rows, row = [], []
    for u in _users():
        mark = "●" if u.is_active else "○"
        row.append({"text": f"{mark} {u.username}",
                    "callback_data": f"{mode}:{u.username}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⬅️ Menu", "callback_data": "v:menu"}])
    return {"inline_keyboard": rows}


def user_text(u: User) -> str:
    accounts = _count_lines(safe_file(_user_dir(u), "accounts.txt"))
    emails = _count_lines(safe_file(_user_dir(u), "emails.txt"))
    r = context.runners.get(u.workspace_key)
    f = context.farms.get(u.workspace_key)
    status = "en cours" if (r and r.is_running()) else "arrêté"
    farm = "active" if (f and f.running) else "arrêtée"
    return (f"<b>👤 {esc(u.username)}</b>\n"
            f"Rôle : {esc(u.role)}\n"
            f"Compte actif : {'oui' if u.is_active else 'non'}\n"
            f"Dernière connexion : {_fmt_ts(u.last_login_at)} ({_ago(u.last_login_at)})\n"
            f"Comptes X : <b>{accounts}</b> · e-mails : <b>{emails}</b>\n"
            f"Job : {status} · Ferme : {farm}")


def user_keyboard(u: User) -> dict:
    return {"inline_keyboard": [
        [{"text": "▶️ Lancer une action", "callback_data": f"a:{u.username}"}],
        [{"text": "🌾 Ferme", "callback_data": f"f:{u.username}"}],
        [{"text": "⬅️ Utilisateurs", "callback_data": "v:users"}],
    ]}


def actions_keyboard(username: str) -> dict:
    rows, row = [], []
    for num in sorted(ACTION_NAMES):
        row.append({"text": f"{num}. {ACTION_NAMES[num]}",
                    "callback_data": f"x:{username}:{num}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⬅️ Utilisateurs", "callback_data": "v:run"},
                 {"text": "🏠 Menu", "callback_data": "v:menu"}])
    return {"inline_keyboard": rows}


def actions_text(username: str) -> str:
    return (f"<b>▶️ {esc(username)} — choisir une action</b>\n\n"
            "Les fichiers d'entrée (tweets, cibles, e-mails…) sont ceux du "
            "workspace : le bot utilise ce qui est déjà enregistré.")


def confirm_keyboard(username: str, num: int) -> dict:
    return {"inline_keyboard": [
        [{"text": f"✅ Démarrer « {ACTION_NAMES[num]} »",
          "callback_data": f"go:{username}:{num}"}],
        [{"text": "✖️ Annuler", "callback_data": f"a:{username}"}],
    ]}


def confirm_text(username: str, num: int) -> str:
    return (f"<b>Confirmer</b>\n\n"
            f"Utilisateur : {esc(username)}\n"
            f"Action : <b>{num}. {esc(ACTION_NAMES[num])}</b>")


def job_status_text(username: str) -> str:
    u = _user(username)
    if not u:
        return "Utilisateur introuvable."
    r = _runner_for(u)
    s = r.status() or {}
    if not s.get("running") and not s.get("total"):
        return f"<b>▶️ {esc(username)}</b>\nAucun job en cours."
    log_lines = []
    for entry in list(s.get("log") or [])[-8:]:
        mark = "✅" if entry.get("ok") else "⚠️"
        log_lines.append(f"{mark} {esc(entry.get('msg', ''))}")
    return (f"<b>▶️ {esc(username)} — job</b>\n"
            f"Action : {esc(s.get('action_name', '—'))}\n"
            f"En cours : {'oui' if s.get('running') else 'non'}\n"
            f"Traités : {s.get('total', 0)} · réussis {s.get('success', 0)} · "
            f"échecs {s.get('failed', 0)}\n"
            + ("\n".join(log_lines) if log_lines else ""))


def farm_text(username: str) -> str:
    u = _user(username)
    if not u:
        return "Utilisateur introuvable."
    f = _farm_for(u)
    s = f.status()
    rows = s.get("rows") or []
    lines = [f"<b>🌾 Ferme — {esc(username)}</b>",
             f"Active : {'oui' if s.get('running') else 'non'}"]
    if s.get("cfg"):
        cfg = s["cfg"]
        acts = ", ".join(f"{k}×{v}" for k, v in (cfg.get("actions") or {}).items() if v)
        lines.append(f"Durée : {cfg.get('duration_days', '—')} j · {esc(acts)}")
    if rows:
        lines.append("")
        for r in rows[:10]:
            lines.append(f"{esc(r.get('account', '?'))} — score "
                         f"{r.get('score', 0)} ({esc(r.get('label', ''))})")
    return "\n".join(lines)


def farm_keyboard(username: str) -> dict:
    return {"inline_keyboard": [
        [{"text": "🟢 Démarrer", "callback_data": f"fs:{username}"},
         {"text": "🔴 Arrêter", "callback_data": f"fx:{username}"}],
        [{"text": "🔄 Rafraîchir", "callback_data": f"f:{username}"}],
        [{"text": "⬅️ Utilisateurs", "callback_data": "v:farm"},
         {"text": "🏠 Menu", "callback_data": "v:menu"}],
    ]}


def logins_text(limit: int = 15) -> str:
    rows = (session().query(AuditLog)
            .filter(AuditLog.action.in_(("login.ok", "login.fail", "login.lockout")))
            .order_by(AuditLog.id.desc()).limit(limit).all())
    if not rows:
        return "<b>🔐 Connexions</b>\n\nAucun événement enregistré."
    lines = ["<b>🔐 Dernières connexions</b>", ""]
    for r in rows:
        mark = {"login.ok": "✅", "login.fail": "❌", "login.lockout": "🔒"}.get(r.action, "•")
        detail = f" ({esc(r.detail)})" if r.detail else ""
        lines.append(f"{mark} {_fmt_ts(r.ts)} — <b>{esc(r.username or '?')}</b>"
                     f" — {esc(r.ip or 'ip ?')}{detail}")
    return "\n".join(lines)


def logins_keyboard() -> dict:
    return {"inline_keyboard": [
        [{"text": "🔄 Rafraîchir", "callback_data": "v:login"}],
        [{"text": "⬅️ Menu", "callback_data": "v:menu"}],
    ]}


def server_text() -> str:
    def human(n: int) -> str:
        for unit in ("o", "Ko", "Mo", "Go"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} To"

    boot = time.time() - _uptime_seconds()
    return ("<b>🖥 Serveur</b>\n\n"
            f"Environnement : {esc(settings.ENV)}\n"
            f"Base : {esc(settings.DATABASE_URL.split('://')[0])}\n"
            f"Démarré : {_fmt_ts(dt.datetime.fromtimestamp(boot, dt.timezone.utc))} "
            f"({_ago(dt.datetime.fromtimestamp(boot, dt.timezone.utc))})\n"
            f"Utilisateurs : {len(_users())}\n"
            f"Jobs en mémoire : {len(context.runners)} · "
            f"fermes en mémoire : {len(context.farms)}")


def _uptime_seconds() -> float:
    """Uptime du host (Linux) ; 0 si indisponible (Windows)."""
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


# ── Bot ──────────────────────────────────────────────────────────────────────

class TelegramBot:
    def __init__(self, client: TelegramClient, admin_username: str,
                 store: AdminStore, pinned_id: int | None = None):
        self.client = client
        self.admin_username = (admin_username or "").lstrip("@")
        self.store = store
        state = store.load()
        self.admin_id = pinned_id or state.get("admin_id")
        self.admin_chat_id = state.get("chat_id") or self.admin_id
        self.offset = 0
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._audit_id = self._max_audit_id()
        self._job_state: dict[str, bool] = {}

    # ── cycle de vie ──
    def start(self):
        if not self._threads:
            for target in (self._poll_loop, self._audit_loop, self._job_watch_loop):
                t = threading.Thread(target=target, daemon=True)
                t.start()
                self._threads.append(t)
            log.info("telegram bot started (admin=@%s, pinned=%s)",
                     self.admin_username, self.admin_id or "non")

    def stop(self):
        self._stop.set()

    # ── boucle principale ──
    def _poll_loop(self):
        backoff = 1
        while not self._stop.is_set():
            try:
                updates = self.client.call(
                    "getUpdates", offset=self.offset, timeout=POLL_TIMEOUT,
                    allowed_updates=["message", "callback_query"]) or []
                backoff = 1
                for update in updates:
                    self.offset = max(self.offset, int(update["update_id"]) + 1)
                    try:
                        self._handle(update)
                    except Exception:
                        log.exception("telegram: erreur de traitement d'un update")
            except TelegramError as e:
                if "409" in str(e) or "Conflict" in str(e):
                    log.error("telegram: conflit de polling — un autre processus "
                              "utilise ce token")
                else:
                    log.warning("telegram: %s", e)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 60)

    def _audit_loop(self):
        """Prévient l'admin des connexions au panneau, en temps réel."""
        while not self._stop.wait(AUDIT_INTERVAL):
            if not self.admin_chat_id:
                continue
            try:
                rows = (session().query(AuditLog)
                        .filter(AuditLog.id > self._audit_id,
                                AuditLog.action.in_(("login.ok", "login.fail",
                                                     "login.lockout")))
                        .order_by(AuditLog.id).all())
                for r in rows:
                    self._audit_id = max(self._audit_id, r.id)
                    self._notify_login(r)
            except Exception:
                log.exception("telegram: veille des connexions")

    def _job_watch_loop(self):
        """Prévient l'admin quand un job se termine."""
        while not self._stop.wait(5):
            for key, runner in list(context.runners.items()):
                try:
                    running = runner.is_running()
                except Exception:
                    continue
                was = self._job_state.get(key, False)
                self._job_state[key] = running
                if was and not running:
                    self._notify_job_end(key, runner)

    def _notify_job_end(self, key: str, runner):
        if not self.admin_chat_id:
            return
        try:
            u = session().query(User).filter_by(workspace_key=key).first()
            username = u.username if u else key
        except Exception:
            username = key
        s = runner.status() or {}
        text = (f"🏁 <b>Job terminé — {esc(username)}</b>\n"
                f"Action : {esc(s.get('action_name', '—'))}\n"
                f"Traités : {s.get('total', 0)} · ✅ {s.get('success', 0)} · "
                f"⚠️ {s.get('failed', 0)}")
        if s.get("last_error"):
            text += f"\nDernière erreur : {esc(s['last_error'])}"
        self._send_text(self.admin_chat_id, text)

    def _notify_login(self, row: AuditLog):
        mark = {"login.ok": "✅ Connexion", "login.fail": "❌ Échec de connexion",
                "login.lockout": "🔒 Compte verrouillé"}.get(row.action, row.action)
        self._send_text(
            self.admin_chat_id,
            f"{mark} — <b>{esc(row.username or '?')}</b>\n"
            f"{_fmt_ts(row.ts)} · {esc(row.ip or 'ip ?')}"
            + (f"\n{esc(row.detail)}" if row.detail else ""))

    def _max_audit_id(self) -> int:
        try:
            row = session().query(AuditLog).order_by(AuditLog.id.desc()).first()
            return row.id if row else 0
        except Exception:
            return 0

    # ── envoi ──
    def _send_text(self, chat_id, text, keyboard=None):
        text = text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "…"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        if keyboard:
            payload["reply_markup"] = keyboard
        try:
            return self.client.call("sendMessage", **payload)
        except TelegramError as e:
            log.warning("telegram: envoi impossible (%s)", e)
            return None

    def _edit(self, chat_id, message_id, text, keyboard=None):
        text = text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "…"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text,
                   "parse_mode": "HTML", "disable_web_page_preview": True}
        if keyboard:
            payload["reply_markup"] = keyboard
        try:
            return self.client.call("editMessageText", **payload)
        except TelegramError as e:
            if "not modified" not in str(e):
                log.warning("telegram: édition impossible (%s)", e)
            return None

    # ── réception ──
    def _handle(self, update: dict):
        if "callback_query" in update:
            cq = update["callback_query"]
            sender = cq.get("from") or {}
            if not self._allow(sender):
                self.client.call("answerCallbackQuery",
                                 callback_query_id=cq["id"],
                                 text="⛔ Accès refusé", show_alert=True)
                return
            self.client.call("answerCallbackQuery", callback_query_id=cq["id"])
            chat_id = ((cq.get("message") or {}).get("chat") or {}).get("id")
            message_id = (cq.get("message") or {}).get("message_id")
            self._route(chat_id, message_id, cq.get("data", ""), via_message=False)
            return

        msg = update.get("message") or {}
        sender = msg.get("from") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        if not chat_id:
            return
        if not self._allow(sender):
            self._send_text(chat_id, "⛔ Ce bot n'est pas ouvert à ce compte.")
            log.warning("telegram: accès refusé à @%s (id=%s)",
                        sender.get("username"), sender.get("id"))
            return
        text = (msg.get("text") or "").strip()
        if not text:
            return
        command = text.split()[0].split("@")[0].lower()
        route = {"/start": "v:menu", "/menu": "v:menu",
                 "/status": "v:dash", "/help": "v:help"}.get(command, "v:menu")
        log.info("telegram: %s → %s", sender.get("username") or sender.get("id"),
                 command if text.startswith("/") else "texte")
        self._route(chat_id, None, route, via_message=True)

    def _allow(self, sender: dict) -> bool:
        ok = is_authorized(sender.get("id", 0), sender.get("username", ""),
                           self.admin_id, self.admin_username)
        if ok and not self.admin_id:
            # Premier contact légitime : on épingle l'ID définitif.
            self.admin_id = int(sender["id"])
            self.admin_chat_id = int(sender["id"])
            self.store.save({"admin_id": self.admin_id,
                             "chat_id": self.admin_chat_id,
                             "username": sender.get("username", "")})
            log.info("telegram: administrateur épinglé (id=%s)", self.admin_id)
        return ok

    # ── routage des écrans ──
    def _route(self, chat_id, message_id, data: str, via_message: bool):
        parts = data.split(":")
        head = parts[0] if parts else ""

        def show(text, keyboard, replace=True):
            if message_id and not via_message and replace:
                self._edit(chat_id, message_id, text, keyboard)
            else:
                self._send_text(chat_id, text, keyboard)

        if head == "v" and len(parts) > 1:
            view = parts[1]
            if view == "menu":
                show(main_menu_text(), main_menu_keyboard())
            elif view == "dash":
                show(dashboard_text(), main_menu_keyboard())
            elif view == "users":
                show(USERS_HEADER, users_keyboard("u"))
            elif view == "run":
                show(run_header(), users_keyboard("a"))
            elif view == "farm":
                show(farm_header(), users_keyboard("f"))
            elif view == "login":
                show(logins_text(), logins_keyboard())
            elif view == "server":
                show(server_text(), main_menu_keyboard())
            elif view == "help":
                show(help_text(), main_menu_keyboard())
            return

        if head == "u" and len(parts) > 1:
            u = _user(parts[1])
            if not u:
                show("Utilisateur introuvable.", main_menu_keyboard())
                return
            show(user_text(u), user_keyboard(u))
            return

        if head == "a" and len(parts) > 1:
            show(actions_text(parts[1]), actions_keyboard(parts[1]))
            return

        if head == "x" and len(parts) > 2:
            username, num = parts[1], _int(parts[2])
            if num not in ACTION_NAMES:
                show("Action inconnue.", main_menu_keyboard())
                return
            show(confirm_text(username, num), confirm_keyboard(username, num))
            return

        if head == "go" and len(parts) > 2:
            self._start_job(chat_id, message_id, parts[1], _int(parts[2]), show)
            return

        if head == "f" and len(parts) > 1:
            show(farm_text(parts[1]), farm_keyboard(parts[1]))
            return

        if head == "fs" and len(parts) > 1:
            u = _user(parts[1])
            if not u:
                show("Utilisateur introuvable.", main_menu_keyboard())
                return
            err = _farm_for(u).start({})
            show(("Fermée démarrée." if not err else f"Erreur : {esc(err)}")
                 + "\n\n" + farm_text(parts[1]), farm_keyboard(parts[1]))
            return

        if head == "fx" and len(parts) > 1:
            u = _user(parts[1])
            if not u:
                show("Utilisateur introuvable.", main_menu_keyboard())
                return
            err = _farm_for(u).stop()
            show(("Ferme arrêtée." if not err else f"Erreur : {esc(err)}")
                 + "\n\n" + farm_text(parts[1]), farm_keyboard(parts[1]))
            return

        show(main_menu_text(), main_menu_keyboard())

    def _start_job(self, chat_id, message_id, username: str, num: int, show):
        u = _user(username)
        if not u:
            show("Utilisateur introuvable.", main_menu_keyboard())
            return
        farm = context.farms.get(u.workspace_key)
        if farm and farm.running:
            show(f"<b>⛔ Ferme en cours</b>\n\nArrête d'abord la ferme de "
                 f"{esc(username)} avant de lancer un job manuel.",
                 user_keyboard(u))
            return
        runner = _runner_for(u)
        err = runner.start(num, _config(u), _user_dir(u))
        if err:
            show(f"<b>❌ Démarrage impossible</b>\n\n{esc(err)}", user_keyboard(u))
            return
        from .audit import log_action
        log_action("job.start", username=username,
                   detail=f"{ACTION_NAMES[num]} (telegram)")
        show(f"<b>✅ Job lancé</b>\n\n{esc(username)} — "
             f"{esc(ACTION_NAMES[num])}\n\n{job_status_text(username)}",
             user_keyboard(u))


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


# ── Démarrage depuis l'app ───────────────────────────────────────────────────

_singleton: TelegramBot | None = None


def start_from_settings() -> TelegramBot | None:
    """Démarre le bot si un token est configuré (idempotent)."""
    global _singleton
    if _singleton is not None:
        return _singleton
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        log.info("telegram: TELEGRAM_BOT_TOKEN absent — bot désactivé")
        return None
    store = AdminStore(os.path.join(settings.DATA_ROOT, "telegram.json"))
    client = TelegramClient(token)
    bot = TelegramBot(client, settings.TELEGRAM_ADMIN, store,
                      pinned_id=settings.TELEGRAM_ADMIN_ID or None)
    bot.start()
    _singleton = bot
    return bot
