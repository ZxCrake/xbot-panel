"""Banques de contenu de vie pour la ferme + récupération d'IDs viraux.

Trois canaux générables automatiquement :

- ``users``     : comptes « mainstream » à suivre (banque statique, sans @) —
                  ce que tout le monde suit, signal humain classique ;
- ``posts``     : posts organiques depuis gabarits spintax ``{a|b}`` FR/EN —
                  RENVOYÉS BRUTS DE SPINTAX : chaque compte/jour re-tire au
                  hasard via ``farm.mutate_text`` → variété par construction ;
- ``tweet_ids`` : IDs de tweets récents de très gros comptes, récupérés en
                  direct sur la timeline publique de syndication (celle des
                  widgets embarqués X — lecture seule, sans auth).

Aucune écriture fichier ici : la route renvoie les lignes, l'utilisateur
relit la zone de texte (le JS a déjà fusionné/dédoublonné) et clique
« Enregistrer le contenu ».
"""

import random
import re

import requests

# ── Comptes à suivre (grands comptes légitimes, suivis par des millions) ──────
USERS_BANK = [
    # science / espace / photo
    "NASA", "SpaceX", "natgeo", "NASAAstronauts",
    # médias mondiaux
    "BBCBreaking", "Reuters", "AP", "CNN", "guardian", "SkyNews",
    # tech
    "Google", "YouTube", "Microsoft", "OpenAI", "Android",
    # personnalités monde
    "elonmusk", "BillGates", "cristiano", "leomessi", "neymarjr",
    # médias FR
    "franceinfo", "BFMTV", "lemondefr", "le_Parisien", "libe",
    "HuffPostFR", "Konbini",
    # sport FR / foot
    "lequipe", "RMCsport", "ActuFoot", "footmercato", "PSG_inside",
    "OM_Officiel", "realmadrid", "ChampionsLeague", "UEFA",
    "FIFAWorldCup", "RolandGarros", "LeTour", "F1", "redbullracing",
    # institutions
    "Elysee", "Interieur_Gouv", "ONU_francais",
]

_USER_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")

# ── Posts organiques (gabarits spintax — banal, sans menace ni lien) ──────────
# Les lignes RENVOYÉES gardent le spintax brut : farm.mutate_text applique à
# chaque publication un tirage + 40 % emoji + 15 % ponctuation flottante.

POSTS_BANK_FR = [
    "{Salut|Coucou|Hello} {tout le monde|la team}, {comment ça va|ça roule|la forme} {aujourd'hui|ce matin|ce soir} {?|!|😄|🙂|👋}",
    "{Bonjour|Bonsoir} à tous, {bonne journée|bonne soirée|bon courage} {à vous|à toute l'équipe} {.|!|✨|🙂|👊}",
    "{GM|GM GM} {les lève-tôt|la famille|☀️|🚀}, {on y va|en route} {pour une bonne journée|} {.|!|☀️|💪}",
    "{Petit|Bon} café du matin {avant de commencer|pour bien démarrer|en terrasse} {.|!|☕|😌}",
    "{Réunion|Présentation} du matin {enfin terminée|en préparation|qui traîne un peu} {…|!|😅|😬}",
    "{Deadline|Livraison} {cette semaine|vendredi}, {on tient le bon bout|ça va le faire|courage à tous} {.|!|💪|🤞}",
    "{Pause déjeuner|Déjeuner} {bien mérité|avec les collègues|au soleil pour une fois} {.|!|😋|🥗|🌞}",
    "{Le lundi est dur|Dur lundi} {comme d'habitude|cette semaine}, {mais on avance|on va y arriver} {.|!|😅|💪}",
    "{Enfin vendredi|Vendredi enfin} {.|!|🎉|🙌|😎} {Bon week-end|Bon WE} {à tous|tout le monde} {.|!|🎉}",
    "{Week-end|Dimanche} {pluie|football|barbecue|repos} {au programme|avec la famille} {.|!|🙂|😌|⚽}",
    "{Nouvelle saison de ma série préférée|Épisode de la série du moment} {hier soir|ce week-end}, {pas mal du tout|mieux que prévu} {.|!|🍿|👌}",
    "{Petit footing|Session sport} {ce matin|ce soir}, {ça fait du bien|les jambes vont le sentir} {.|!|🏃|💪|😅}",
    "{Canicule en approche|Il fait lourd aujourd'hui}, {restons hydratés|ventilateur de sortie} {.|!|☀️|💧}",
    "{Le code compile du premier coup|Bug résolu après 3 heures}, {jour béni|soulagement immense} {.|!|😎|🥳}",
    "{Grève|Retard} des transports {ce matin|encore}, {journée qui commence bien|patience infinie donc} {…|!|😑|😅}",
    "{Trop de pluie ces derniers jours|Le soleil est enfin revenu}, {le moral remonte|ça change tout} {.|!|☀️|🌈}",
    "{Petite victoire perso aujourd'hui|Objectif de la semaine atteint} {.|!|🔥|🎯|💪}",
    "{Qui regarde le match ce soir|Résultat du match d'hier impressionnant} {?|!|⚽|👀}",
    "{Croissant|Chocolatine} du matin, {le débat reste ouvert|petit plaisir simple} {.|!|🥐|😋}",
    "{Playlist du jour en boucle|Nouvel album en écoute} {en travaillant|au bureau} {.|!|🎧|🎶}",
    "{Rdv chez le dentiste demain|Réunion parent-profs ce soir}, {la vie d'adulte glamour|c'est ça aussi le quotidien} {.|!|😅|🙃}",
    "{Bonne nuit la team|Dodo time}, {à demain|grosses journées en perspective} {.|!|😴|🌙}",
    "{Petit message sympa d'un client aujourd'hui|Retour positif sur le projet}, {ça motive énormément|c'est pour ça qu'on le fait} {.|!|🙏|💙}",
    "{Nettoyage de printemps sur le disque dur|Backup enfin terminé}, {ordre numérique retrouvé|conscience tranquille} {.|!|🧹|✅}",
]

POSTS_BANK_EN = [
    "{Hey|Hi|Hello} {everyone|all|folks}, {how's it going|how are you} {today|this morning} {?|!|😄|🙂|👋}",
    "{Morning|Good evening} everyone, {have a great day|stay safe|take care} {out there|folks} {.|!|✨|🙂}",
    "{GM|GM GM} {friends|fam|☀️|🚀}, {let's go|we move} {.|!|💪|☀️}",
    "{Coffee|Morning coffee} {before anything else|to kick things off} {.|!|☕|😌}",
    "{Finally Friday|Friday at last} {.|!|🎉|🙌} {Have a great weekend|Enjoy the weekend} {y'all|everyone} {.|!|🎉}",
    "{Slow Monday as usual|Tough Monday}, {but we push through|let's get it done} {.|!|💪|😅}",
    "{Little win today|Small victory today} {.|!|🔥|🎯|💪}",
    "{Lunch break|Lunchtime} {well earned|with the team|outside in the sun} {.|!|😋|🌞}",
    "{Code compiled on first try|Bug fixed after 3 hours}, {blessed day|huge relief} {.|!|😎|🥳}",
    "{Too much rain lately|Rainy days are hitting different}, {where's the sun|can't wait for spring} {…|!|☔|🌈}",
    "{Long run this morning|Gym session done}, {legs will feel it tomorrow|feeling great though} {.|!|🏃|💪}",
    "{New episode tonight|That show last night was wild}, {no spoilers please|who else is watching} {?|!|🍿|👀}",
    "{Standup meeting done|Back to back calls today}, {now real work begins|need another coffee} {.|!|☕|😅}",
    "{Weekend BBQ plans|Sunday chill mode}, {finally some rest|good vibes only} {.|!|😌|🙂}",
    "{Playlist on repeat today|This new album hits}, {work mode activated|perfect background} {.|!|🎧|🎶}",
    "{Great feedback from a client today|Positive review came in}, {keeps me going|this is why we do it} {.|!|🙏|💙}",
    "{Traffic was brutal this morning|Train delayed again}, {classic start of the week|patience is a virtue} {…|!|😑|😅}",
    "{Hydrate people|Sun is finally back}, {summer vibes loading|positive energy} {.|!|☀️|💧}",
    "{Big presentation tomorrow|Deadline this week}, {we're almost there|final push} {.|!|💪|🤞}",
    "{Started journaling this week|Trying meditation again}, {small habits matter|day three feeling good} {.|!|✍️|🧘}",
    "{Late night coding session|Weekend project ideas}, {need more coffee soon|brain won't stop} {…|!|😴|☕}",
    "{Cleaning my desk at last|Inbox zero achieved}, {digital peace restored|fresh start} {.|!|🧹|✅}",
    "{Just adopted a plant|My plant is dying again}, {wish me luck|any plant tips here} {?|!|🪴|🌱}",
]

# Comptes sources d'IDs viraux (postent beaucoup, engagement massif)
_TWEET_SOURCES = ["NASA", "BBCBreaking", "YouTube", "natgeo", "elonmusk",
                  "franceinfo", "realmadrid", "lequipe"]

_SYND_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}?dnt=true&frame=false"
_TWEET_ID_RE = re.compile(r"/status/(\d{8,})")
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Statuts vus à la dernière tentative (diag pour la route)
LAST_STATUS = {"saw_429": False, "saw_network_error": False}


def _proxy_dict(proxy: str):
    if not proxy:
        return None
    p = proxy if "://" in proxy else "http://" + proxy
    return {"http": p, "https": p}


def fetch_recent_tweet_ids(handles, limit_per_handle=15, timeout=10, proxy=""):
    """IDs de tweets récents via timeline de syndication (sans auth).

    Lecture seule, tolérante aux pannes : un échec de source n'interrompt pas
    les autres. Passe par `proxy` si fourni (palie le rate-limit par IP de
    syndication). Mémoire diag dans LAST_STATUS. Renvoie des IDs dédoublonnés.
    """
    found, seen = [], set()
    LAST_STATUS.update(saw_429=False, saw_network_error=False)
    proxies = _proxy_dict(proxy)
    for h in handles:
        try:
            r = requests.get(_SYND_URL.format(handle=h), headers=_HEADERS,
                             timeout=timeout, proxies=proxies)
            if r.status_code == 429:
                LAST_STATUS["saw_429"] = True
                continue
            if r.status_code != 200:
                continue
            for m in _TWEET_ID_RE.finditer(r.text):
                tid = m.group(1)
                if tid not in seen:
                    seen.add(tid)
                    found.append(tid)
                    if len(found) >= limit_per_handle * len(handles):
                        return found
        except requests.RequestException:
            LAST_STATUS["saw_network_error"] = True
            continue
    return found


# ── Cache anti rate-limit (les IDs viraux restent exploitables 24 h) ──────────

CACHE_FILE = "tweet_ids_gen_cache.json"
CACHE_TTL = 86400  # 24 h


def _cache_path(base_dir: str) -> str:
    import os
    from .files import safe_file
    return safe_file(base_dir, CACHE_FILE)


def cache_write(base_dir: str, ids: list):
    import json, time
    try:
        with open(_cache_path(base_dir), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "ids": ids[:200]}, f)
    except OSError:
        pass


def cache_read(base_dir: str) -> list:
    """IDs cachés s'il y a moins de CACHE_TTL, sinon []."""
    import json, os, time
    p = _cache_path(base_dir)
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if time.time() - float(d.get("ts", 0)) > CACHE_TTL:
            return []
        return [str(i) for i in d.get("ids", []) if str(i).isdigit()][:200]
    except (OSError, ValueError, TypeError):
        return []


# ── Banque d'images (posts organiques avec média) ────────────────────────────

MEDIA_EXTS = (".jpg", ".jpeg", ".png", ".webp")
MAX_MEDIA_BYTES = 4_500_000
_PICSUM = "https://picsum.photos/seed/{seed}/768/576"


def media_dir(base_dir: str) -> str:
    import os
    return os.path.join(base_dir, "media")


def media_bank(base_dir: str) -> list:
    """Chemins des images utilisables dans la banque (triés, taille contrôlée)."""
    import os
    out = []
    try:
        for name in sorted(os.listdir(media_dir(base_dir))):
            if not name.lower().endswith(MEDIA_EXTS):
                continue
            p = os.path.join(media_dir(base_dir), name)
            try:
                if 0 < os.path.getsize(p) <= MAX_MEDIA_BYTES:
                    out.append(p)
            except OSError:
                continue
    except OSError:
        pass
    return out


def fetch_stock_images(base_dir: str, count: int = 10, proxy: str = "",
                       timeout: int = 15) -> int:
    """Télécharge `count` photos libres (picsum/Unsplash) dans la banque.

    Source générique volontairement : pour la vente, chaque client devrait
    curer sa propre banque (unicité d'empreinte visuelle). Écrit directement
    dans media/ (binaire, pas de revue texte) ; renvoie le nombre ajouté.
    """
    import os, random, requests as rq
    os.makedirs(media_dir(base_dir), exist_ok=True)
    added, proxies = 0, _proxy_dict(proxy)
    for _ in range(count):
        seed = f"{random.getrandbits(64):016x}"
        name = f"stock-{seed}.jpg"
        path = os.path.join(media_dir(base_dir), name)
        if os.path.exists(path):
            continue
        try:
            r = rq.get(_PICSUM.format(seed=seed), headers=_HEADERS,
                       timeout=timeout, proxies=proxies)
            if r.status_code != 200 or len(r.content) > MAX_MEDIA_BYTES:
                continue
            with open(path, "wb") as f:
                f.write(r.content)
            added += 1
        except Exception:
            continue
    return added


def generate(channel: str, lang: str = "fr", proxy: str = "") -> list:
    """Lignes prêtes à fusionner dans le contenu de vie.

    channel ∈ users | posts | tweet_ids ; lang ∈ fr | en (posts seulement).
    Valeurs levées : ValueError sur paramètre invalide ; liste vide
    (tweet_ids seulement) si la récupération distante a échoué partout.
    """
    if channel == "users":
        return random.sample(USERS_BANK, min(30, len(USERS_BANK)))
    if channel == "posts":
        bank = POSTS_BANK_EN if lang == "en" else POSTS_BANK_FR
        return random.sample(bank, min(20, len(bank)))
    if channel == "tweet_ids":
        sources = random.sample(_TWEET_SOURCES, k=len(_TWEET_SOURCES))  # toutes, mélangées
        return fetch_recent_tweet_ids(sources, limit_per_handle=8, proxy=proxy)
    raise ValueError("channel must be 'users', 'posts' or 'tweet_ids'")


def sanity_check() -> list:
    """Contrôles statiques des banques — utilisés par les tests."""
    problems = []
    for i, u in enumerate(USERS_BANK):
        if not _USER_HANDLE_RE.match(u):
            problems.append(f"handle invalide #{i}: {u!r}")
    for name, bank in (("fr", POSTS_BANK_FR), ("en", POSTS_BANK_EN)):
        for i, t in enumerate(bank):
            if t.count("{") != t.count("}"):
                problems.append(f"spintax déséquilibré ({name} #{i})")
            if "@" in t or "http" in t.lower():
                problems.append(f"lien ou mention ({name} #{i})")
    return problems
