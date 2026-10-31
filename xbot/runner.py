import json
import os
import time
import random
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Lock, Event, Thread, BoundedSemaphore

from .x.session import XSession
from .x import actions
from . import settings, proxies
from .files import safe_file, profile_path
from .security import validate_config

JOB_SLOTS = BoundedSemaphore(settings.MAX_ACTIVE_JOBS)


class AccessEvent(Event):
    """Notice revocation from another process, including during long pauses."""
    def __init__(self, authorized=None):
        super().__init__()
        self.authorized = authorized

    def is_set(self):
        if not super().is_set() and self.authorized is not None:
            try:
                allowed = self.authorized()
            except Exception:
                allowed = False
            if not allowed:
                super().set()
        return super().is_set()

    def wait(self, timeout=None):
        if self.authorized is None:
            return super().wait(timeout)
        end = None if timeout is None else time.monotonic() + timeout
        while not self.is_set():
            remaining = 1 if end is None else end - time.monotonic()
            if remaining <= 0:
                return False
            if super().wait(min(1, remaining)):
                return True
        return True

ACTION_NAMES = {
    1: "Quote Tweet",
    2: "Retweet",
    3: "Like",
    4: "Reply",
    5: "View Tweet",
    6: "Bookmark",
    7: "Cross Follow",
    8: "Change PFP",
    9: "Change Name/Bio",
    10: "Check Premium",
    11: "Publish Article",
    12: "Follow Target",
    13: "Send DM",
    14: "Change Email",
}

# Actions qui itèrent sur tweet_ids.txt
TWEET_ID_ACTIONS = (2, 3, 4, 5, 6)
# Actions exécutées une seule fois par compte (pas de répétition par limit)
ONCE_ACTIONS = (7, 8, 9, 10, 11, 12, 13, 14)
# Actions dont les cibles (users.txt) sont réparties entre les comptes
TARGET_ACTIONS = (1, 12, 13)


# ── File helpers ──────────────────────────────────────────────────────────────

def load_json_file(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_lines(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


class TargetPool:
    """File partagée et thread-safe des cibles (mentions / follows / DM).

    Chaque cible apparaît `per_target` fois, le tout mélangé, et chaque élément
    n'est consommé qu'UNE fois, globalement. Contrairement à l'ancienne
    pré-partition figée, un compte qui échoue (auth, proxy mort) ne consomme
    aucune cible : les cibles restantes restent disponibles pour les comptes
    suivants — la cible n'est jamais perdue avec son compte.
    Le plafond anti-spam (≤ per_target mentions d'une même cible) est préservé.
    """

    def __init__(self, usernames: list, per_target: int = 1):
        self._pool = list(usernames) * max(1, int(per_target))
        random.shuffle(self._pool)
        self._lock = Lock()

    def take(self, n: int = 1) -> list:
        """Jusqu'à `n` cibles, atomiquement ([] quand la file est épuisée)."""
        if n <= 0:
            return []
        with self._lock:
            out = self._pool[:n]
            del self._pool[:n]
            return out

    def remaining(self) -> int:
        with self._lock:
            return len(self._pool)


def pick_mentions(usernames: list, n: int) -> list:
    """Return up to n randomly-chosen usernames (raw, without '@')."""
    n = min(max(int(n), 0), len(usernames))
    return random.sample(usernames, n) if n > 0 else []


# ── Stats + log (thread-safe) ───────────────────────────────────────────────────

class JobStats:
    def __init__(self, action_name: str, total_accounts: int, history_path: str = ""):
        self._lock = Lock()
        self.action_name = action_name
        self.total_accounts = total_accounts
        self.total = 0
        self.success = 0
        self.failed = 0
        self.hidden = 0
        self.accounts_done = 0
        self.start_time = time.time()
        self.log = deque(maxlen=300)
        self.history_path = history_path

    def _persist(self, ok: bool, msg: str):
        if not self.history_path or not msg:
            return
        try:
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "t": time.time(),
                    "ok": ok,
                    "action": self.action_name,
                    "msg": msg,
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def record_ok(self, msg: str = ""):
        with self._lock:
            self.total += 1
            self.success += 1
            if msg:
                self.log.append({"t": time.time(), "ok": True, "msg": msg})
        self._persist(True, msg)

    def record_fail(self, msg: str = ""):
        with self._lock:
            self.total += 1
            self.failed += 1
            if msg:
                self.log.append({"t": time.time(), "ok": False, "msg": msg})
        self._persist(False, msg)

    def record_hidden(self, msg: str = ""):
        """Tweet créé mais masqué par X (visibilité réduite / spam flag)."""
        with self._lock:
            self.total += 1
            self.hidden += 1
            if msg:
                self.log.append({"t": time.time(), "ok": False, "msg": msg})
        self._persist(False, msg)

    def record_account_done(self):
        with self._lock:
            self.accounts_done += 1

    def to_dict(self) -> dict:
        with self._lock:
            elapsed = int(time.time() - self.start_time)
            rate = (self.success / self.total * 100) if self.total else 0
            return {
                "action_name": self.action_name,
                "total_accounts": self.total_accounts,
                "total": self.total,
                "success": self.success,
                "failed": self.failed,
                "hidden": self.hidden,
                "accounts_done": self.accounts_done,
                "elapsed": elapsed,
                "rate": round(rate, 1),
                "log": list(self.log),
            }


# ── Per-account worker ────────────────────────────────────────────────────────

def _sleep_between(cfg: dict, stop_event: Event):
    lo = cfg.get("delay_min", 1)
    hi = cfg.get("delay_max", 3)
    stop_event.wait(random.uniform(lo, max(lo, hi)))


def run_account(acc: str, action_mode: int, cfg: dict, stats: JobStats,
                pools: dict, stop_event: Event, target_pool: "TargetPool | None" = None):
    try:
        if target_pool is None:
            _run_account(acc, action_mode, cfg, stats, pools, stop_event)
        else:
            _run_account(acc, action_mode, cfg, stats, pools, stop_event, target_pool)
    finally:
        stats.record_account_done()


def _run_account(acc: str, action_mode: int, cfg: dict, stats: JobStats,
                 pools: dict, stop_event: Event, target_pool: "TargetPool | None" = None):
    if stop_event.is_set():
        return

    acc = acc.strip()
    username = acc.split(":")[0]

    # L'index du compte dans accounts.txt lui choisit son proxy (cfg injectée
    # par la boucle d'envoi ; 0 = premier proxy / fallback partagé).
    account_index = cfg.get("_account_index", 0)
    if not isinstance(account_index, int) or account_index < 0:
        account_index = 0

    with XSession(auth_token=acc.split(":")[-1],
                  proxy=proxies.resolve_for_account(cfg, account_index),
                  stop_event=stop_event) as sess:
        _run_session(sess, username, action_mode, cfg, stats, pools, stop_event, target_pool)


def _run_session(sess, username, action_mode, cfg, stats, pools, stop_event,
                 target_pool: "TargetPool | None" = None):
    if not sess.authenticate():
        stats.record_fail(f"@{username} - Auth failed")
        return

    limit = cfg.get("limit", 1)
    tweet_ids = pools["tweet_ids"]

    for _ in range(limit):
        if stop_event.is_set():
            break

        if action_mode == 1:
            text = random.choice(pools["tweets"])["text"]
            # Cibles tirées de la file partagée (consommées une fois,
            # globalement) — les comptes morts n'en consomment aucune.
            if target_pool is not None:
                selected = target_pool.take(cfg.get("select_users", 3))
            else:
                selected = pick_mentions(pools["users"], cfg.get("select_users", 3))
            if not selected and int(cfg.get("select_users", 3)) > 0:
                stats.record_fail(f"@{username} - no target available "
                                  "(shared target pool exhausted)")
                break

            # Optionally follow each mentioned account first — a follow
            # relationship makes the mention far more likely to push a
            # notification (X filters mentions from non-followed accounts).
            if cfg.get("follow_mentioned"):
                for target in selected:
                    if stop_event.is_set():
                        break
                    if actions.follow(sess, target):
                        stats.record_ok(f"@{username} followed @{target}")
                    else:
                        stats.record_fail(f"@{username} - follow @{target} failed")
                    _sleep_between(cfg, stop_event)

            if stop_event.is_set():
                break
            mentions = " ".join(f"@{u}" for u in selected)
            # Position aléatoire des mentions (début/fin) pour casser les
            # patterns détectés par X.
            mentions_first = bool(cfg.get("random_mention_position", 1)) \
                and bool(random.getrandbits(1))
            ok, rest_id, vis = actions.quote_tweet(sess, text, mentions,
                                                   mentions_first=mentions_first)
            if ok and vis:
                stats.record_hidden(f"@{username} post HIDDEN by X ({vis}) → {mentions} "
                                    "— account likely flagged, no notif sent")
            elif ok:
                stats.record_ok(f"@{username} posted quote → {mentions}")
            else:
                stats.record_fail(f"@{username} - Quote failed")

        elif action_mode in TWEET_ID_ACTIONS:
            for tid in tweet_ids:
                if stop_event.is_set():
                    break
                vis = ""
                if action_mode == 2:
                    ok = actions.retweet(sess, tid)
                    label = "retweeted"
                elif action_mode == 3:
                    ok = actions.like(sess, tid)
                    label = "liked"
                elif action_mode == 4:
                    text = random.choice(pools["replies"])["text"]
                    ok, _, vis = actions.reply(sess, tid, text)
                    label = "replied to"
                elif action_mode == 5:
                    ok = actions.view_tweet(sess, tid)
                    label = "viewed"
                else:  # 6
                    ok = actions.bookmark(sess, tid)
                    label = "bookmarked"

                if ok and vis:
                    stats.record_hidden(f"@{username} {label} HIDDEN by X ({vis}) ({tid})")
                elif ok:
                    stats.record_ok(f"@{username} {label} {tid}")
                else:
                    stats.record_fail(f"@{username} - {label} failed ({tid})")
                _sleep_between(cfg, stop_event)

        elif action_mode == 12:
            # Notification « X vous suit » — la plus fiable de X. Les cibles
            # viennent de la file partagée : un compte qui échoue n'en perd
            # aucune, les comptes vivants épuisent la file à sa place.
            took_any = False
            while True:
                if stop_event.is_set():
                    break
                if target_pool is not None:
                    batch = target_pool.take(1)
                    if not batch:
                        break
                    follow_targets = batch
                elif not took_any:
                    follow_targets = list(pools["users"])
                else:
                    break
                for target in follow_targets:
                    took_any = True
                    if stop_event.is_set():
                        break
                    ok = actions.follow(sess, target)
                    if ok:
                        stats.record_ok(f"@{username} followed @{target}")
                    else:
                        stats.record_fail(f"@{username} - Follow failed (@{target})")
                    _sleep_between(cfg, stop_event)
            if not took_any:
                stats.record_fail(f"@{username} - no target available "
                                  "(shared target pool exhausted)")
                return

        elif action_mode == 13:
            # DM — arrive en « demande de message » : déclenche une notif même
            # chez un inconnu, contrairement aux mentions filtrées.
            # Cibles tirées de la file partagée (failover entre comptes).
            took_any = False
            while True:
                if stop_event.is_set():
                    break
                if target_pool is not None:
                    batch = target_pool.take(1)
                    if not batch:
                        break
                    dm_targets = batch
                elif not took_any:
                    dm_targets = list(pools["users"])
                else:
                    break
                for target in dm_targets:
                    took_any = True
                    if stop_event.is_set():
                        break
                    uid, err = actions.resolve_user_id(sess, target)
                    if not uid:
                        stats.record_fail(f"@{username} - @{target} introuvable ({err})")
                        _sleep_between(cfg, stop_event)
                        continue
                    text = random.choice(pools["dms"])["text"]
                    if actions.send_dm(sess, uid, text):
                        stats.record_ok(f"@{username} DM → @{target}")
                    else:
                        stats.record_fail(f"@{username} - DM failed (@{target})")
                    _sleep_between(cfg, stop_event)
            if not took_any:
                stats.record_fail(f"@{username} - no target available "
                                  "(shared target pool exhausted)")
                return

        elif action_mode == 14:
            # Nouvelle adresse e-mail = ligne suivante de la file partagée
            # `emails.txt` (format `adresse:mot_de_passe_gmail`). Le mot de
            # passe transmis à la mutation est celui du compte X (champ n°2
            # de accounts.txt quand présent ; '' sinon).
            if target_pool is not None:
                batch = target_pool.take(1)
            else:
                batch = pools.get("emails", [])[:1]
            if not batch:
                stats.record_fail(f"@{username} - no email available "
                                  "(shared pool exhausted)")
                return
            new_email, _, _gpass = str(batch[0]).partition(":")
            x_pass = str(cfg.get("_account_password", "") or "")
            if not new_email:
                stats.record_fail(f"@{username} - invalid line in emails.txt")
                return
            if actions.change_email(sess, new_email, x_pass):
                stats.record_ok(f"@{username} email set to {new_email}")
            else:
                stats.record_fail(f"@{username} - email update failed")

        elif action_mode == 7:
            follow_targets = [u for u in pools["all_usernames"] if u.lower() != username.lower()]
            for target in follow_targets:
                if stop_event.is_set():
                    break
                ok = actions.follow(sess, target)
                if ok:
                    stats.record_ok(f"@{username} followed @{target}")
                else:
                    stats.record_fail(f"@{username} - Follow failed (@{target})")
                _sleep_between(cfg, stop_event)

        elif action_mode == 8:
            ok = actions.update_profile_picture(sess, pools["profile_path"])
            if ok:
                stats.record_ok(f"@{username} updated profile picture")
            else:
                stats.record_fail(f"@{username} - PFP update failed")

        elif action_mode == 9:
            ok = actions.update_profile(sess, cfg.get("display_name", ""), cfg.get("bio", ""))
            if ok:
                stats.record_ok(f"@{username} updated name/bio")
            else:
                stats.record_fail(f"@{username} - Name/bio update failed")

        elif action_mode == 10:
            info = actions.check_premium(sess, username)
            if not info["ok"]:
                stats.record_fail(f"@{username} - premium check failed ({info['error']})")
            elif info["premium"]:
                vt = f" ({info['verified_type']})" if info["verified_type"] else ""
                stats.record_ok(f"@{username} — PREMIUM ✔{vt}")
            else:
                stats.record_fail(f"@{username} — no Premium")

        elif action_mode == 11:
            info = actions.check_premium(sess, username)
            if not info["ok"]:
                stats.record_fail(f"@{username} - premium check failed ({info['error']})")
            elif not info["premium"]:
                stats.record_fail(f"@{username} — skipped (no Premium)")
            else:
                for art in pools["articles"]:
                    if stop_event.is_set():
                        break
                    ok, ref = actions.publish_article(sess, art)
                    title = art.get("title", "untitled")
                    if ok:
                        stats.record_ok(f"@{username} published article “{title}”")
                    else:
                        stats.record_fail(f"@{username} - article “{title}” failed ({ref})")
                    _sleep_between(cfg, stop_event)

        if action_mode in ONCE_ACTIONS:
            break

        if limit > 1:
            lo = cfg.get("account_delay_min", 10)
            hi = cfg.get("account_delay_max", 25)
            stop_event.wait(random.uniform(lo, max(lo, hi)))


# ── Pool loading + validation ───────────────────────────────────────────────────

def build_pools(action_mode: int, base_dir: str = ".") -> dict:
    p = lambda name: safe_file(base_dir, name)
    accounts = load_lines(p("accounts.txt"))
    pools = {
        "accounts": accounts,
        "all_usernames": [a.split(":")[0] for a in accounts],
        "tweet_ids": load_lines(p("tweet_ids.txt")) if action_mode in TWEET_ID_ACTIONS else [],
        "tweets": load_json_file(p("tweets.txt")) if action_mode == 1 else [],
        "replies": load_json_file(p("reply.txt")) if action_mode == 4 else [],
        "users": load_lines(p("users.txt")) if action_mode in TARGET_ACTIONS else [],
        "dms": load_json_file(p("dms.txt")) if action_mode == 13 else [],
        "emails": load_lines(p("emails.txt")) if action_mode == 14 else [],
        "articles": (load_json_file(p("articles.json"))
                     if action_mode == 11 and os.path.exists(p("articles.json")) else []),
    }
    return pools


def validate(action_mode: int, cfg: dict, pools: dict, base_dir: str = ".") -> str:
    """Retourne un message d'erreur, ou '' si tout est ok."""
    if not pools["accounts"]:
        return "No X accounts imported"
    if len(pools["accounts"]) > settings.MAX_ACCOUNTS_PER_JOB:
        return f"At most {settings.MAX_ACCOUNTS_PER_JOB} accounts per job"
    proxy_err = proxies.coverage_error(cfg, len(pools["accounts"]))
    if proxy_err:
        return proxy_err
    if action_mode == 1 and not pools["tweets"]:
        return "No posts written (add your texts in the task)"
    if action_mode in TARGET_ACTIONS and not pools["users"]:
        return "No target specified"
    if action_mode == 13 and not pools["dms"]:
        return "No DM text written"
    if action_mode == 4 and not pools["replies"]:
        return "No reply text written"
    if action_mode in TWEET_ID_ACTIONS and not pools["tweet_ids"]:
        return "No tweet ID specified"
    if action_mode == 8:
        try:
            path = profile_path(base_dir, cfg.get("pfp_image", "pfp.jpg"))
        except ValueError as e:
            return str(e)
        if not os.path.isfile(path):
            return f"Profile image not found: {cfg.get('pfp_image', 'pfp.jpg')}"
        if os.path.getsize(path) > settings.MAX_PFP_BYTES:
            return "Profile image too large"
        pools["profile_path"] = path
    if action_mode == 9 and not cfg.get("display_name", "") and not cfg.get("bio", ""):
        return "Set display_name and/or bio"
    if action_mode == 11 and not pools["articles"]:
        return "no articles — create or import at least one"
    if action_mode == 14:
        if not pools["emails"]:
            return "No new emails — add them in emails.txt (adresse:mot_de_passe)"
        if len(pools["emails"]) < len(pools["accounts"]):
            return (f"{len(pools['emails'])} email(s) for "
                    f"{len(pools['accounts'])} account(s) in emails.txt; "
                    "add one line per account")
    return ""


# ── BotRunner : pilote un job en arrière-plan ────────────────────────────────────

class BotRunner:
    def __init__(self, authorized=None):
        self._lock = Lock()
        self.authorized = authorized
        self.stats: JobStats | None = None
        self.stop_event = Event()
        self._thread: Thread | None = None
        self.running = False
        self.last_error = ""
        self._retired = False

    def is_running(self) -> bool:
        return self.running

    def start(self, action_mode: int, cfg: dict, base_dir: str = ".") -> str:
        with self._lock:
            if self._retired:
                return "User access has been revoked"
            if self.running:
                return "A job is already running"
            try:
                if action_mode not in ACTION_NAMES:
                    return "Invalid action"
                cfg = {**settings.DEFAULT_CONFIG, **validate_config(cfg)}
                pools = build_pools(action_mode, base_dir)
            except FileNotFoundError as e:
                return f"Missing file: {e.filename}"
            except json.JSONDecodeError as e:
                return f"Invalid JSON: {e}"
            except (ValueError, OSError) as e:
                return str(e)

            err = validate(action_mode, cfg, pools, base_dir)
            if err:
                return err
            history_path = safe_file(base_dir, "history.log")
            if not JOB_SLOTS.acquire(blocking=False):
                return "Server job capacity reached; try again after a job finishes"

            self.stop_event = AccessEvent(self.authorized)
            self.stats = JobStats(ACTION_NAMES[action_mode], len(pools["accounts"]), history_path)
            self.running = True
            self.last_error = ""
            self._thread = Thread(
                target=self._run, args=(action_mode, cfg, pools), daemon=True
            )
            try:
                self._thread.start()
            except Exception:
                self.running = False
                JOB_SLOTS.release()
                raise
            return ""

    def _run(self, action_mode: int, cfg: dict, pools: dict):
        try:
            num_threads = max(1, int(cfg.get("threads", 5)))
            # Actions à cibles (1, 12, 13) : file partagée — chaque cible est
            # consommée une fois globalement (≤ mentions_per_target fois par
            # cible). Un compte qui échoue (auth, proxy) ne consomme rien :
            # les comptes suivants prennent les cibles restantes à sa place.
            target_pool = None
            if action_mode in TARGET_ACTIONS:
                target_pool = TargetPool(
                    pools["users"], cfg.get("mentions_per_target", 1))
            elif action_mode == 14:
                # Une adresse par compte, consommée une seule fois globalement.
                target_pool = TargetPool(pools["emails"], 1)
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                accounts = iter(enumerate(pools["accounts"]))
                pending = set()
                exhausted = False
                while pending or not exhausted:
                    while not exhausted and len(pending) < num_threads and not self.stop_event.is_set():
                        item = next(accounts, None)
                        if item is None:
                            exhausted = True
                            break
                        idx, acc = item
                        # Par-compte : index (proxy) + mot de passe X quand
                        # présent (champ n°2 d'un accounts.txt à 3 colonnes).
                        parts = acc.split(":")
                        cfg_i = {**cfg, "_account_index": idx,
                                 "_account_password": parts[1] if len(parts) > 2 else ""}
                        pending.add(executor.submit(
                            run_account, acc, action_mode, cfg_i,
                            self.stats, pools, self.stop_event,
                            target_pool))
                    if not pending:
                        break
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for f in done:
                        try:
                            f.result()
                        except Exception:
                            # Network exceptions can contain proxy credentials.
                            if not self.stop_event.is_set():
                                self.stats.record_fail("Account processing failed")
        except Exception as e:
            self.last_error = str(e)
        finally:
            with self._lock:
                self.running = False
                JOB_SLOTS.release()

    def retire(self):
        """Permanently prevent starts, including through an in-flight request."""
        with self._lock:
            self._retired = True
            self.stop_event.set()

    def stop(self) -> str:
        with self._lock:
            if not self.running:
                return "No job running"
            self.stop_event.set()
            return ""

    def status(self) -> dict:
        s = self.stats.to_dict() if self.stats else {}
        s["running"] = self.running
        s["last_error"] = self.last_error
        return s
