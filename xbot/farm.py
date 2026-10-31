"""Farm — réchauffement autonome des comptes ("humanisation").

Principe : des comptes dormants doivent accumuler des jours d'activité banale,
banale = ce que fait un humain (suivre, liker, scroller, poster de temps en
temps), à toute heure du jour, à faible cadence, chaque jour. Le
scheduler génère chaque nuit, pour chaque compte, un plan d'actions datées en
heure locale, puis les exécute au fil du temps — sans mentions, sans liens,
sans rafales (toujours ≤ 1 action par tick et par compte).

Score d'humanisation (0-100), calculé en continu à partir de mesures réelles :

- visibilité (40 pts) : proportion de tweets récents NON masqués par X
  (détection __typename = TweetWithVisibilityResults / tombstone, déjà
  implémentée côté actions.py) — c'est LA mesure de flag X ;
- croissance organique (20) : followers gagnés depuis le démarrage de la
  ferme, lus chaque jour via UserByScreenName (_lookup_user) ;
- profondeur d'activité (20) : nb de jours distincts avec activité réussie
  (objectif : 14) ;
- profil (10) : nom d'affichage + bio + photo configurés (déjà vus côté
  réchauffement manuel actions 8/9) ;
- intégrité (10) : pas d'échec d'auth récent (compte locké/suspendu).

Status persistant dans farm_state.json (plan, compteurs, historiques) : la ferme
redémarre proprement après un restart du service.
"""

import json
import os
import random
import time
import uuid
from collections import deque
from threading import Event, Lock, Thread

from . import farm_content, proxies
from .files import safe_file
from .x import actions
from .x import media as xmedia
from .x.session import XSession

STATE_FILE = "farm_state.json"

# Fenêtre de mémoire pour la santé de visibilité (tweets récents par compte)
VIS_WINDOW = 50
GROWTH_TARGET = 50          # followers organiques à viser (20 pts du score)
DEPTH_TARGET = 14           # jours distincts d'activité (20 pts)
AUTH_FAIL_TRIP = 3          # failed d'auth consécutifs → compte "compromised"
AUTH_FAIL_WINDOW = 86400    # fenêtre de mémoire des failed (s)

# Actions de vie disponibles, avec le canal de contenu qu'elles consomment.
# 0 dans la config = action désactivée. Les canaux se remplissent dans la carte
# « Life content » du panneau (boutons Generate inclus).
ACTION_KINDS = ("follow", "like", "retweet", "bookmark", "view", "tweet")
ACTION_CHANNELS = {
    "follow":   "users",
    "like":     "tweet_ids",
    "retweet":  "tweet_ids",
    "bookmark": "tweet_ids",
    "view":     "tweet_ids",
    "tweet":    "tweets",
}


def estimate_ready_days(st: dict, profile_ready: bool, now: float) -> tuple:
    """ETA (jours calendaires) jusqu'au score ≥ 70 selon la trajectoire observée.

    Projection honnête : croissance des followers au rythme mesuré, jours
    actifs au rythme du profil, visibilité supposée constante. Renvoie
    (jours, note) ; jours = None et note non vide quand la trajectoire ne
    peut pas atteindre 70 (ou pas avec les données disponibles).
    """
    if st.get("status") == "compromised":
        return None, "compromised"
    days_done = active_days(st)
    growth_now = max(0, _volume(st, "followers") - _volume(st, "followers_at_start"))
    vis_log = [v for v in st.get("vis", []) if v is not None]
    vis = (sum(1 for v in vis_log if v) / len(vis_log)) if vis_log else 1.0
    lock = 0 if (_consec_fails(st) >= AUTH_FAIL_TRIP
                 or sum(1 for f in st.get("auth_fail_ts", [])
                        if f > now - AUTH_FAIL_WINDOW) >= AUTH_FAIL_TRIP) else 1
    prof = 1 if profile_ready else 0
    ok_ts = st.get("ok_ts") or []
    span_days = max(1.0, (now - min(ok_ts)) / 86400.0) if ok_ts else 1.0
    r_g = growth_now / span_days          # followers / jour calendaire (observé)
    p_a = 1.0                             # jours actifs / jour calendaire (jamais de repos)

    base = 40 * vis + 10 * prof + 10 * lock

    def score_at(t: float) -> float:
        g = 20 * min(1.0, (growth_now + r_g * t) / GROWTH_TARGET)
        d = 20 * min(1.0, (days_done + p_a * t) / DEPTH_TARGET)
        return base + g + d

    if score_at(10**9) < 70:
        if vis < 1.0 and vis_log:
            return None, "posts hidden"
        if r_g <= 0.0 and growth_now < GROWTH_TARGET:
            return None, "no follower growth"
        return None, "trajectory too weak"
    lo, hi = 0.0, 1.0
    while score_at(hi) < 70:
        hi *= 2
        if hi > 36500:
            return None, "trajectory too weak"
    for _ in range(60):
        mid = (lo + hi) / 2
        if score_at(mid) >= 70:
            hi = mid
        else:
            lo = mid
    return hi, ""

_TWEET_ID_KINDS = ("like", "retweet", "bookmark", "view")

EMOJI_POOL = ("👍", "🙏", "✨", "😅", "😄", "🤔", "🔥", "😉", "🙌", "😊", "🫡")


# ── Texte : mutation spintax-légère (pas deux tweets identiques en une vie) ──

def mutate_text(raw: str) -> str:
    """Rend un texte unique : {a|b} au hasard, emoji-frôle, ponctuation flottante.

    Ne fait pas de magie : la variété structurelle vient de votre pool. Les
    mutations ci-dessous cassent la signature « texte à l'identique » entre
    comptes et entre jours.
    """
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "{" and "}" in raw[i:]:
            j = raw.index("}", i)
            seg = raw[i + 1:j]
            if "|" in seg:
                out.append(random.choice(seg.split("|")))
            else:
                out.append(raw[i:j + 1])
            i = j + 1
        else:
            out.append(raw[i])
            i += 1
    text = "".join(out).strip()

    if text and random.random() < 0.40:
        text = f"{text} {random.choice(EMOJI_POOL)}"
    if text and random.random() < 0.15 and text[-1] in ".!?":
        text = text[:-1] + random.choice(["…", "!", "!!", text[-1]])
    return text


# ── Config custom d'un run (valide à la demande, cf. panneau Farm) ───────────

def validate_farm_cfg(raw: dict) -> tuple:
    """Valide une config de run personnalisée. Renvoie (cfg propre, erreur).

    Requis :
    - duration_days : entier 1..365 (la ferme s'arrête seule au bout de N jours)
    - actions : {follow, like, retweet, bookmark, view, tweet} ≥ 0, somme > 0
    - variation_min / variation_max : % optionnels (50..100), appliqués par
      compte et par jour (défaut 80..100 — fluctuation humaine pas trop forte)
    """
    if not isinstance(raw, dict):
        return None, "cfg must be an object"
    dur = raw.get("duration_days")
    if not isinstance(dur, int) or isinstance(dur, bool) or not (1 <= dur <= 365):
        return None, "duration_days must be an integer between 1 and 365"
    acts = raw.get("actions")
    if not isinstance(acts, dict):
        return None, "actions must be an object like {'follow': 2, 'like': 5}"
    counts = {}
    for kind in ACTION_KINDS:
        n = acts.get(kind, 0)
        if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > 100:
            return None, f"actions.{kind} must be an integer between 0 and 100"
        counts[kind] = n
    total = sum(counts.values())
    if total == 0:
        return None, "enable at least one action (all counts are 0)"
    if total > 100:
        return None, "total actions per account per day must stay under 100"
    vmin = raw.get("variation_min", 80)
    vmax = raw.get("variation_max", 100)
    for v in (vmin, vmax):
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 100):
            return None, "variation_min/max must be integers between 1 and 100 (%)"
    if vmin > vmax:
        return None, "variation_min must be ≤ variation_max"
    return {
        "duration_days": dur,
        "actions": counts,
        "variation_min": vmin,
        "variation_max": vmax,
    }, ""


# ── Planification quotidienne ─────────────────────────────────────────────────

def generate_plan(day: str, day_epoch: float, accounts: list, cfg: dict,
                  content: dict, used: dict = None) -> tuple:
    """Plan d'aujourd'hui : ({account: [entries...]}, (kinds épuisés, mis à jour)).

    Chaque action de `cfg["actions"]` produit `count` exécutions par compte,
    pondérées par un facteur aléatoire par compte et par jour dans
    [variation_min, variation_max] % (défaut 80–100 %). Les cibles sont tirées
    SANS répétition pendant tout le run (`used` = {account: {kind: set}}),
    horodatées uniformément sur 24 h, ≤ 1 action/compte/tick par ailleurs.
    """
    lo, hi = day_epoch, day_epoch + 86400
    span = max(1.0, hi - lo)
    if used is None:
        used = {}
    exhausted = []
    plans = {}
    for acc in accounts:
        user = acc.split(":")[0]
        my_used = used.setdefault(user, {})
        factor = random.randint(cfg.get("variation_min", 80),
                                cfg.get("variation_max", 100)) / 100.0
        entries = []
        for kind in ACTION_KINDS:
            n = cfg.get("actions", {}).get(kind, 0)
            if n <= 0:
                continue
            channel = ACTION_CHANNELS[kind]
            pool = list(content.get(channel) or [])
            if kind == "follow":
                pool = [u for u in pool
                        if u.lower() not in content.get("usernames", set())
                        and u.lower() != user.lower()]
            already = my_used.setdefault(kind, set())
            avail = [t for t in pool if t not in already]
            want = max(1, int(round(n * factor)))
            if not avail:
                if len(pool) > 0:
                    exhausted.append((kind, user))
                continue
            take = avail[:min(want, len(avail))]
            already.update(take)
            for tgt in take:
                ts = lo + random.random() * span
                entries.append({"id": uuid.uuid4().hex[:12], "ts": ts, "kind": kind,
                                "target": tgt, "status": "pending", "detail": ""})
        # garde-fou : si tout est filtré (compte à zéro après variation), on laisse
        # vide — la cadence réelle du compte reste positive EXCEPT si variation < 50 %
        entries.sort(key=lambda e: e["ts"])
        plans[user] = entries
    return plans, exhausted


def run_progress(state: dict) -> dict:
    """Progression du run en cours : {duration_days, day_index, left_days,
    ends_at, completed}. Vide si aucune durée n'est configurée."""
    run = state.get("run") or {}
    dur = int(run.get("duration_days", 0) or 0)
    if dur <= 0:
        return {}
    start = float(run.get("start", 0) or 0)
    now = time.time()
    elapsed = (now - start) / 86400.0 if start else 0.0
    return {
        "duration_days": dur,
        "day_index": min(dur, max(1, int(elapsed) + 1)),
        "left_days": max(0, dur - int(elapsed)),
        "ends_at": start + dur * 86400.0,
        "completed": bool(run.get("completed", False)),
    }


# ── Score d'humanisation ──────────────────────────────────────────────────────

def active_days(state: dict) -> int:
    return len({t // 86400 for t in state.get("ok_ts", [])})


def humanization_score(state: dict, farm_started: float, cfg_profile_ready: bool) -> float:
    vis_log = state.get("vis", [])
    tweets = sum(1 for v in vis_log if v is not None)
    vis = (sum(1 for v in vis_log if v) / tweets) if tweets else 0.0
    growth = max(0, _volume(state, "followers") - _volume(state, "followers_at_start"))
    depth = active_days(state)
    recent_fails = sum(1 for f in state.get("auth_fail_ts", [])
                       if f > time.time() - AUTH_FAIL_WINDOW)
    # les points d'intégrité n'existent que s'il y a une mesure :
    # un compte sans aucune activité observée ne gagne rien « gratuitement »
    measured = bool(state.get("ok_ts") or state.get("auth_fail_ts") or state.get("vis"))
    lock = 0
    if measured and not (_consec_fails(state) >= AUTH_FAIL_TRIP
                         or recent_fails >= AUTH_FAIL_TRIP):
        lock = 1
    return round(
        40 * vis
        + 20 * min(1.0, growth / GROWTH_TARGET)
        + 20 * min(1.0, depth / DEPTH_TARGET)
        + 10 * (1 if cfg_profile_ready else 0)
        + 10 * lock)


def _volume(state: dict, key: str) -> int:
    return int(state.get(key, 0) or 0)


def _consec_fails(state: dict) -> int:
    """Nb d'échecs d'auth d'affilée (depuis le dernier succès)."""
    last_ok = max(state.get("ok_ts", [0])) if state.get("ok_ts") else 0
    return sum(1 for f in state.get("auth_fail_ts", []) if f > last_ok)


def score_label(score: float, status: str) -> str:
    if status == "compromised":
        return "compromised"
    if score >= 70:
        return "ready"
    if score >= 30:
        return "warming"
    return "dormant"


# ── Status persistant ───────────────────────────────────────────────────────────

class FarmState:
    """Charge/sauvegarde farm_state.json de façon atomique."""

    def __init__(self, path: str):
        self.path = path
        self._lock = Lock()
        self.data = {
            "v": 1, "running": False, "cfg": {}, "started": 0,
            "plans": {},       # date (YYYY-MM-DD) → {user: [entries]}
            "accounts": {},    # user → counters/history
        }

    def load(self):
        with self._lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    if isinstance(d, dict) and d.get("v") == 1:
                        self.data = {**self.data, **d}
                except (OSError, json.JSONDecodeError):
                    pass

    def save(self):
        with self._lock:
            try:
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False)
                os.replace(tmp, self.path)
            except OSError:
                pass

    def account(self, user: str) -> dict:
        acc = self.data.setdefault("accounts", {}).setdefault(user, {})
        vis = acc.get("vis", [])
        if not isinstance(vis, list):
            vis = []
        acc["vis"] = vis[-VIS_WINDOW:]
        acc.setdefault("ok_ts", [])
        acc.setdefault("auth_fail_ts", [])
        acc.setdefault("followers", 0)
        acc.setdefault("followers_at_start", None)
        acc.setdefault("status", "dormant")
        acc.setdefault("done", {})
        return acc


# ── Moteur ────────────────────────────────────────────────────────────────────

class FarmRunner:
    def __init__(self, base_dir: str, authorized=None):
        self.base_dir = base_dir
        self.authorized = authorized
        self._lock = Lock()
        self.stop_event = Event()
        self._thread: Thread | None = None
        self.running = False
        self.last_error = ""
        self.log = deque(maxlen=300)
        self.state = FarmState(safe_file(base_dir, STATE_FILE))
        self.state.load()

    # ─ style helpers ─
    def _say(self, msg: str):
        self.log.append({"t": time.time(), "msg": msg})

    # ─ lifecycle ─
    def start(self, cfg_updates: dict) -> str:
        with self._lock:
            if self.running:
                return "Farm is already running"
            cfg, err = validate_farm_cfg(cfg_updates or {})
            if err:
                return err
            content = self._load_content()
            if not content["accounts"]:
                return "No X accounts imported"
            try:
                with open(safe_file(self.base_dir, "config.json"), encoding="utf-8") as f:
                    pcfg = json.load(f)
                perr = proxies.coverage_error(pcfg, len(content["accounts"]))
                if perr:
                    return perr
            except (OSError, ValueError):
                pass
            missing = [kind for kind in ACTION_KINDS
                       if cfg["actions"][kind] > 0
                       and not content[ACTION_CHANNELS[kind]]]
            if missing:
                return ("Fill the Life content channels for: "
                        + ", ".join(missing) + " (Farm tab)")
            self.state.data["cfg"] = cfg
            self.state.data["started"] = self.state.data.get("started") or time.time()
            self.state.data["run"] = {
                "duration_days": cfg["duration_days"],
                "start": time.time(),
                "completed": False,
            }
            self.state.data["used"] = {}
            self.stop_event = Event()
            self.running = True
            self.last_error = ""
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()
            self.state.data["running"] = True
            self.state.save()
            per_day = sum(cfg["actions"].values())
            self._say("farm started (%d day(s), ~%d action(s)/account/day, %d accounts)"
                      % (cfg["duration_days"], per_day, len(content["accounts"])))
            return ""

    def maybe_resume(self):
        """Redémarre la boucle si l'état persistant dit « running »."""
        if self.state.data.get("running") and not self.running:
            self.stop_event = Event()
            self.running = True
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()
            self._say("farm resumed after service restart")

    def stop(self) -> str:
        with self._lock:
            if not self.running:
                return "No farm running"
            self.stop_event.set()
            self.state.data["running"] = False
            self.state.save()
            return ""

    def _finish_thread(self):
        self.running = False
        self.state.data["running"] = False
        self.state.save()

    # ─ contenu ─
    def _load_content(self) -> dict:
        def lines(name):
            try:
                with open(safe_file(self.base_dir, name), encoding="utf-8") as f:
                    return [ln.strip() for ln in f if ln.strip()]
            except (OSError, ValueError):
                return []
        def jlines(name):
            try:
                with open(safe_file(self.base_dir, name), encoding="utf-8") as f:
                    d = json.load(f)
                return [o.get("text", "") for o in d if o.get("text")]
            except (OSError, ValueError, TypeError):
                return []
        accounts = lines("accounts.txt")
        return {
            "accounts": accounts,
            "usernames": {a.split(":")[0] for a in accounts},
            "users": lines("users.txt"),
            "tweet_ids": lines("tweet_ids.txt"),
            "tweets": jlines("tweets.txt"),
            "media": farm_content.media_bank(self.base_dir),
        }

    # ─ boucle principale ─
    def _run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    self._tick()
                    self._heartbeat()
                except Exception as e:
                    self.last_error = str(e)
                # cadence de tick voilée (45-75 s)
                self.stop_event.wait(random.uniform(45, 75))
        finally:
            self._finish_thread()

    def _heartbeat(self):
        """Ligne de log « preuve de vie » si rien n'a été dit depuis 30 min :
        progression du jour + prochaine action. Aucune info sensible (pas de
        noms de comptes/cibles, IP, tokens) — juste des compteurs et minutes."""
        engine = self.state.data.get("engine", {})
        if not engine.get("last_tick"):
            return
        last_log = self.log[-1]["t"] if self.log else 0
        if time.time() - last_log < 1800:
            return
        planned, done = engine.get("planned", 0), engine.get("done", 0)
        reason_text = {
            "plan_exhausted": "today's plan finished",
            "no_content": "no life content — nothing to act on",
            "no_accounts": "no accounts imported",
            "no_active_accounts": "all accounts paused",
            "completed": "run completed",
            "invalid_cfg": "invalid farm config — stop and restart with a custom config",
        }.get(engine.get("reason", ""))
        msg = f"engine alive — {done}/{planned} actions done today"
        if engine.get("reason") == "waiting" and engine.get("next_due"):
            mins = max(1, int((engine["next_due"] - time.time()) // 60))
            self._say(f"{msg}, next action in ~{mins} min")
        elif reason_text:
            self._say(f"{msg} ({reason_text})")
        else:
            self._say(msg)

    def _today(self):
        now = time.time()
        day_epoch = now - (now % 86400)
        day = time.strftime("%Y-%m-%d", time.gmtime(day_epoch))
        return day, day_epoch, now

    def _tick(self):
        day, day_epoch, now = self._today()
        content = self._load_content()
        cfg = self.state.data.get("cfg", {})
        engine = self.state.data.setdefault("engine", {})
        engine.pop("window", None)  # rimasuglio del vecchio gating per finestra
        engine["last_tick"] = now
        engine["ticks"] = int(engine.get("ticks", 0)) + 1

        # fin de la durée du run ?
        run = self.state.data.get("run") or {}
        if run.get("duration_days") and not run.get("completed"):
            if now >= run.get("start", 0) + run["duration_days"] * 86400:
                run["completed"] = True
                self.state.data["run"] = run
                engine.update({"next_due": None, "reason": "completed"})
                self._say(f"farm run completed ({run['duration_days']} day(s)) — all accounts delivered")
                self.stop_event.set()
                self.state.data["running"] = False
                self.state.save()
                return
        if run.get("completed"):
            # le run est fini : le moteur ne fait plus rien (arrêt déjà demandé)
            self.stop_event.set()
            return

        # config héritée / invalide (ex. ancien format "profile") : ne planifier
        # rien et dire clairement quoi faire — silence would look like a hang.
        valid_cfg, _cfg_err = validate_farm_cfg(cfg)
        if valid_cfg is None:
            engine.update({"planned": 0, "pending": 0, "done": 0, "failed": 0,
                           "next_due": None, "reason": "invalid_cfg"})
            self.state.save()
            return

        if not content["accounts"]:
            engine.update({"planned": 0, "pending": 0, "done": 0, "failed": 0,
                           "next_due": None, "reason": "no_accounts"})
            self.state.save()
            return

        plans = self.state.data.setdefault("plans", {})
        if day not in plans:
            used_state = self.state.data.setdefault("used", {})
            used = {u: {k: set(v) for k, v in kinds.items()}
                    for u, kinds in used_state.items()}
            for acc in content["accounts"]:
                used.setdefault(acc.split(":")[0], {})
            new_plans, exhausted = generate_plan(
                day, day_epoch, content["accounts"], cfg, content, used)
            plans[day] = new_plans
            # les sets consommés ne sont pas JSON-sérialisables : on réécrit
            # en listes triées avant la sauvegarde
            self.state.data["used"] = {u: {k: sorted(v) for k, v in kinds.items()}
                                       for u, kinds in used.items()}
            # ne garde que 3 jours de plans en mémoire
            if len(plans) > 3:
                for k_ in sorted(plans)[:-3]:
                    plans.pop(k_, None)
            total = sum(len(v) for v in plans[day].values())
            active = sum(1 for v in plans[day].values() if v)
            msg = f"plan {day}: {total} actions across {active}/{len(content['accounts'])} accounts"
            if exhausted:
                kinds = sorted({k for k, _ in exhausted})
                msg += " — pool exhausted: " + ", ".join(kinds)
            self._say(msg)
            self.state.save()

        # Télémétrie du jour + collecte des actions dues (compteurs calculés
        # avant exécution : les actions de CE tick entrent au prochain tick).
        planned = pending = done_today = failed_today = eligible = 0
        next_due = None
        due = []
        for acc in content["accounts"]:
            user = acc.split(":")[0]
            st = self.state.account(user)
            entries_plans = plans[day].get(user, [])
            for entry in entries_plans:
                planned += 1
                stt = entry["status"]
                if stt == "ok":
                    done_today += 1
                elif stt == "error":
                    failed_today += 1
                elif stt == "pending":
                    pending += 1
                    if entry["ts"] > now and (next_due is None or entry["ts"] < next_due):
                        next_due = entry["ts"]
            if _consec_fails(st) >= AUTH_FAIL_TRIP:
                continue
            eligible += 1
            for entry in entries_plans:
                if entry["status"] == "pending" and entry["ts"] <= now:
                    due.append((acc, entry))
                    break  # ≤ 1 action par tick et par compte

        if due:
            reason = ""
        elif pending and eligible == 0 and planned:
            reason = "no_active_accounts"
        elif pending:
            reason = "waiting"
        elif planned:
            reason = "plan_exhausted"
        else:
            reason = "no_content"
        engine.update({"planned": planned, "pending": pending, "done": done_today,
                       "failed": failed_today, "next_due": next_due,
                       "reason": reason})
        self.state.save()

        for acc, entry in due:
            if self.stop_event.is_set():
                break
            self._execute(acc, entry, content)

        # une fois par jour et par compte : lecture des followers
        self._daily_metrics(content, now)

    # ─ exécution d'une action ─
    def _maybe_upload_image(self, sess, content: dict) -> list:
        """~30 % des posts organiques joignent une photo de la banque média.

        Comportement humain normal (photos du quotidien) ; l'échec d'upload
        n'interrompt pas le post (texte seul dans ce cas)."""
        bank = content.get("media") or []
        if not bank or random.random() >= 0.30:
            return []
        path = random.choice(bank)
        try:
            with open(path, "rb") as f:
                data = f.read()
            mime = "image/png" if path.lower().endswith(".png") else (
                "image/webp" if path.lower().endswith(".webp") else "image/jpeg")
            mid = xmedia.upload_image(sess, data, mime)
            return [mid] if mid else []
        except (OSError, ValueError):
            return []

    def _execute(self, acc: str, entry: dict, content: dict):
        user = acc.split(":")[0]
        token = acc.split(":")[-1]
        st = self.state.account(user)
        entry["status"] = "running"
        ok, detail = False, ""
        kind = entry["kind"]
        try:
            account_index = content["accounts"].index(acc)
        except ValueError:
            account_index = 0
        proxy = self._runtime_proxy(account_index)

        try:
            with XSession(auth_token=token, proxy=proxy,
                          stop_event=self.stop_event) as sess:
                if not sess.authenticate():
                    # Un proxy mort ne dit rien sur le compte : ne pas compter
                    # l'échec de transport dans la santé du compte.
                    if sess.last_net_error:
                        entry["status"] = "error"
                        entry["detail"] = "proxy/network error"
                        self.state.save()
                        return
                    st["auth_fail_ts"].append(time.time())
                    entry["status"] = "error"
                    entry["detail"] = "auth failed"
                    if _consec_fails(st) >= AUTH_FAIL_TRIP:
                        st["status"] = "compromised"
                        self._say(f"@{user} compromised (auth ×{AUTH_FAIL_TRIP}) — removed from farm")
                    self.state.save()
                    return

                if kind == "follow":
                    tgt = entry.get("target")
                    if not tgt:
                        ok, detail = True, "no-one to follow"
                    else:
                        ok = actions.follow(sess, tgt)
                        detail = f"follow @{tgt}" if ok else f"follow @{tgt} failed"

                elif kind in _TWEET_ID_KINDS:
                    tid = entry.get("target")
                    if not tid:
                        ok, detail = True, "no tweet_ids"
                    else:
                        fn = {"like": actions.like, "retweet": actions.retweet,
                              "bookmark": actions.bookmark, "view": actions.view_tweet}[kind]
                        ok = fn(sess, tid)
                        detail = f"{kind} {tid}" if ok else f"{kind} {tid} failed"

                elif kind == "tweet":
                    raw = entry.get("target")
                    if not raw:
                        ok, detail = True, "no tweets"
                    else:
                        text = mutate_text(raw)
                        media_ids = self._maybe_upload_image(sess, content)
                        ok, rest_id, vis = actions.quote_tweet(
                            sess, text, "", media_ids=media_ids or None)
                        if ok and vis:
                            st["vis"].append(False)
                            detail = f"tweet HIDDEN ({vis})"
                        elif ok:
                            st["vis"].append(True)
                            detail = "tweet ok"
                        else:
                            st["vis"].append(None)
                            detail = "tweet failed"
        except Exception as e:
            ok, detail = False, f"error: {type(e).__name__}"

        if ok:
            st["ok_ts"].append(time.time())
            st.setdefault("done", {})
            st["done"][kind] = st["done"].get(kind, 0) + 1
            entry["status"] = "ok"
        elif entry["status"] != "ok":
            entry["status"] = "error"
        target = detail
        entry["detail"] = target
        self._say(f"@{user} {detail}")
        self.state.save()

        # borne mémoire vis
        st["vis"] = st.get("vis", [])[-VIS_WINDOW:]
        # rythme inter-action naturel par compte (ne bloque pas le scheduler)
        # — les actions suivantes arrivent via les ticks suivants

    # ─ métriques journalières (followers, 1 lecture/jour/compte, étalées) ─
    def _daily_metrics(self, content: dict, now: float):
        day_epoch = now - (now % 86400)
        for acc in content["accounts"]:
            user = acc.split(":")[0]
            st = self.state.account(user)
            if st.get("metrics_day") == day_epoch or _consec_fails(st) >= AUTH_FAIL_TRIP:
                continue
            try:
                try:
                    account_index = content["accounts"].index(acc)
                except ValueError:
                    account_index = 0
                with XSession(auth_token=acc.split(":")[-1],
                              proxy=self._runtime_proxy(account_index),
                              stop_event=self.stop_event) as sess:
                    if not sess.authenticate():
                        continue
                    result, err = actions._lookup_user(sess, user)
                    if result:
                        current = int(result.get("legacy", {}).get("followers_count", 0) or 0)
                        if st.get("followers_at_start") is None:
                            st["followers_at_start"] = current
                        st["followers"] = current
                        st["metrics_day"] = day_epoch
                    self.state.save()
            except Exception:
                continue
            break  # une seule lecture par tick — le reste s'étale sur les ticks suivants

    # ─ API lecture ─
    def status(self) -> dict:
        content = self._load_content()
        cfg_ready = self._profile_ready()
        now = time.time()
        rows = []
        for acc in content["accounts"]:
            user = acc.split(":")[0]
            st = self.state.account(user)
            status_ = st.get("status", "dormant")
            s = humanization_score(st, self.state.data.get("started", now), cfg_ready)
            eta, eta_note = estimate_ready_days(st, cfg_ready, now)
            rows.append({
                "account": user,
                "score": s,
                "label": score_label(s, status_),
                "eta_days": eta,
                "eta_note": eta_note,
                "followers": _volume(st, "followers"),
                "growth": max(0, _volume(st, "followers") - _volume(st, "followers_at_start")),
                "active_days": active_days(st),
                "tweets_ok": sum(1 for v in st["vis"] if v),
                "tweets_flagged": sum(1 for v in st["vis"] if v is False),
                "done": st.get("done", {}),
                "status": status_,
            })
        rows.sort(key=lambda r: -r["score"])
        return {
            "running": self.running,
            "media_count": len(content.get("media") or []),
            "cfg": self.state.data.get("cfg", {}),
            "started": self.state.data.get("started", 0),
            "last_error": self.last_error,
            "engine": self.state.data.get("engine", {}),
            "run": run_progress(self.state.data),
            "now": now,
            "accounts": rows,
            "log": list(self.log),
        }

    def scores(self) -> dict:
        s = self.status()
        return {"running": s["running"], "accounts":
                [{k: r[k] for k in ("account", "score", "label", "eta_days",
                                    "eta_note", "followers", "growth",
                                    "active_days", "tweets_ok",
                                    "tweets_flagged", "status")}
                 for r in s["accounts"]]}

    def _runtime_proxy(self, account_index: int) -> str:
        """Proxy HTTP pour CE compte (config.json multi-proxies) — relu à chaud."""
        try:
            with open(safe_file(self.base_dir, "config.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            return proxies.resolve_for_account(cfg, account_index)
        except (OSError, ValueError):
            return ""

    def _profile_ready(self) -> bool:
        cfg = self.state.data.get("cfg", {})
        try:
            with open(safe_file(self.base_dir, "config.json"), encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            pass
        name = bool(str(cfg.get("display_name", "")).strip())
        bio = bool(str(cfg.get("bio", "")).strip())
        pfp = os.path.exists(os.path.join(self.base_dir, str(cfg.get("pfp_image", "pfp.jpg"))))
        return name and bio and pfp
