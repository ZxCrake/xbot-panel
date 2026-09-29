> Cette page décrit aussi des formats historiques. Pour les changements de sécurité et la migration, voir [SECURITY_UPDATE.md](SECURITY_UPDATE.md).

# X Automation — Documentation Backend

API JSON multi-users pilotant l'automatisation X (Twitter). Authentification par token Bearer, données cloisonnées par user, jobs exécutés en arrière-plan.

---

## Sommaire

1. [Architecture](#architecture)
2. [Installation](#installation)
3. [Gestion des users (CLI admin)](#gestion-des-users-cli-admin)
4. [Authentification](#authentification)
5. [Référence API](#référence-api)
6. [Format des fichiers](#format-des-fichiers)
7. [Configuration (par user)](#configuration-par-user)
8. [Les actions (1–13)](#les-actions-113)
9. [Farm (réchauffement autonome)](#ferme-réchauffement-autonome)
10. [Organisation des données](#organisation-des-données)
11. [Déploiement](#déploiement)
12. [Sécurité](#sécurité)

---

## Architecture

```
Twitter Quotes/
├── run.py                  # Point d'entrée API (expose `app` pour gunicorn)
├── manage.py               # CLI admin (créer / supprimer / lister les users)
├── requirements.txt
├── xbot/                   # Package backend
│   ├── __init__.py         # create_app() : factory Flask (CORS, blueprints, health)
│   ├── settings.py         # Chemins, config par défaut, CORS
│   ├── auth.py             # Users, hash mots de passe, tokens signés, décorateurs
│   ├── runner.py           # BotRunner : jobs en arrière-plan, stats, historique
│   ├── context.py          # Helpers web (user courant, registre des runners)
│   ├── routes/             # Blueprints : auth.py, user.py, admin.py
│   └── x/                  # Cœur client X
│       ├── constants.py    # Bearer public, user-agent, features GraphQL
│       ├── session.py      # XSession : pipeline d'auth X (ct0, guest token, xpff)
│       ├── actions.py      # Les 9 actions (like, retweet, quote, follow, pfp…)
│       └── xpff.py         # Header chiffré x-xp-forwarded-for
└── data/                   # Données runtime (créé automatiquement)
    ├── users.json
    ├── .secret_key
    └── <username>/         # un dossier isolé par user
```

**Flux d'une requête authentifiée :**
`routes/` (blueprint + décorateur `login_required`) → vérifie le token → `runner.py` (job) → `x/session.py` (auth X) → `x/actions.py` (appel GraphQL).

---

## Installation

```bash
pip install -r requirements.txt
```

Dépendances : `flask`, `curl_cffi`, `beautifulsoup4`, `XClientTransaction`, `pycryptodome`.
(`itsdangerous` et `werkzeug` sont fournis avec Flask.)

Lancement en développement :

```bash
python run.py          # écoute sur 0.0.0.0:5000
```

---

## Gestion des users (CLI admin)

Aucune inscription publique. Les comptes sont créés en ligne de commande ou via l'API admin.

```bash
python manage.py add <username> [password]          # créer un user
python manage.py add <username> <password> admin    # créer un administrateur
python manage.py passwd <username> [password]       # changer un mot de passe
python manage.py del <username>                     # supprimer
python manage.py list                               # lister
```

- `username` : 3 à 32 caractères, `a-z 0-9 _ -` uniquement (mis en minuscules).
- `password` : 6 caractères minimum. Si omis, demandé en saisie masquée.

**Premier admin :**

```bash
python manage.py add boss MonMotDePasse admin
```

---

## Authentification

Token **Bearer signé** (via `itsdangerous`), stateless, valable **7 jours**.

1. Le front appelle `POST /api/login` avec `username` + `password`.
2. Le back renvoie un `token`.
3. Le front envoie ce token sur **chaque** requête suivante :

```
Authorization: Bearer <token>
```

Pas de déconnexion côté serveur : le front jette simplement le token. Les tokens sont signés avec `data/.secret_key` ; supprimer ce fichier invalide tous les tokens existants.

**Codes d'erreur d'auth :**

| Code | Signification |
|------|---------------|
| `401` | Token absent, invalide ou expiré |
| `403` | Token valide mais droits admin requis |

---

## Référence API

Toutes les réponses sont en JSON. Sauf `/api/login` et `/`, toutes les routes exigent l'en-tête `Authorization`.

### Auth

#### `POST /api/login`
Connexion.

Requête :
```json
{ "username": "client1", "password": "secret123" }
```
Réponse `200` :
```json
{ "token": "eyJ1Ijoi...", "username": "client1", "is_admin": false }
```
Réponse `401` : `{ "error": "identifiants invalides" }`

#### `GET /api/me`
```json
{ "username": "client1", "is_admin": false }
```

#### `GET /api/actions`
Liste des actions disponibles.
```json
{ "1": "Quote Tweet", "2": "Retweet", "...": "...", "9": "Change Name/Bio" }
```

---

### Données user

#### `GET /api/config`
Renvoie la config de l'user (valeurs par défaut comprises). Voir [Configuration](#configuration-par-user).

#### `POST /api/config`
Corps = l'objet config complet à enregistrer.
```json
{ "proxy": "user:pass@host:port", "threads": 10, "limit": 1, "select_users": 1 }
```
Réponse : `{ "ok": true }`

#### `GET /api/file/<name>`
`name` ∈ `accounts.txt`, `users.txt`, `tweets.txt`, `reply.txt`, `tweet_ids.txt`.
```json
{ "content": "user1:tok1\nuser2:tok2" }
```
Nom non autorisé → `400 { "error": "file not allowed" }`

#### `POST /api/file/<name>`
```json
{ "content": "user1:tok1\nuser2:tok2" }
```
Réponse : `{ "ok": true }`

#### `POST /api/upload-pfp`
`multipart/form-data`, champ `file` = l'image. Enregistrée sous le nom défini par `pfp_image` dans la config.
```json
{ "ok": true, "saved": "pfp.jpg" }
```

---

### Contrôle des jobs

#### `POST /api/run`
Lance un job pour l'user courant.
```json
{ "action_mode": 3, "config": { "threads": 10 } }
```
- `action_mode` : 1 à 9 (obligatoire).
- `config` : facultatif ; si présent, sauvegardé avant le lancement.

Réponse `200` : `{ "ok": true }`
Réponse `400` : `{ "error": "<raison>" }` (ex. `accounts.txt is empty`, `A job is already running`, `tweet_ids.txt is empty`…)

#### `POST /api/stop`
Demande l'arrêt du job en cours. `{ "ok": true }` ou `400 { "error": "No job running" }`.

#### `GET /api/status`
Status live du job de l'user.
```json
{
  "running": true,
  "action_name": "Like",
  "total_accounts": 50,
  "accounts_done": 12,
  "total": 120,
  "success": 110,
  "failed": 10,
  "hidden": 0,
  "rate": 91.7,
  "elapsed": 84,
  "last_error": "",
  "log": [
    { "t": 1718600000.12, "ok": true,  "msg": "@bob liked 123" },
    { "t": 1718600001.45, "ok": false, "msg": "@alice - Like failed (456)" }
  ]
}
```
`log` : 300 dernières entrées en mémoire. `elapsed` en secondes.

#### `POST /api/farm/start`
Démarre la ferme de réchauffement avec une **config custom validée** (plus de
profils prédéfinis depuis la refonte côté run). `409` si un job manuel tourne.

```json
{
  "duration_days": 14,
  "variation_min": 80,
  "variation_max": 100,
  "actions": {
    "follow": 1, "like": 2, "retweet": 0,
    "bookmark": 0, "view": 2, "tweet": 0
  }
}
```
- `duration_days` ∈ **1–365** (obligatoire) — la ferme s'arrête seule au bout de N
  jours et marque le run `completed`. 
- `variation_min`/`variation_max` ∈ **1–100** (%), `min ≤ max`. Chaque compte tire un
  facteur journalier aléatoire dans cette fourchette et l'applique à CHAQUE compte
  par action — garde-fou : au moins 1 action/jour si `total counts > 0`.
- `actions` : 6 clés (`follow`, `like`, `retweet`, `bookmark`, `view`, `tweet`),
  chacune entier **0–100** ; somme > 0 et ≤ 100. `0` = action désactivée.
- Au démarrage le validateur exige que chaque action de `count > 0` ait son canal
  Life content rempli (erreur `Fill the Life content channels for: <kinds>`).
- `run` persistée (`{ start, duration_days, completed }`) ; les listes `used`
  (consommation anti-répétition des cibles) sont réinitialisées à chaque démarrage.

Le panneau applique des **templates** (slow/gentle/normal/fast) purement côté
front : ils ne pré-remplissent que les champs — le backend ne connaît plus la
notion de profil.

#### `POST /api/farm/stop`
Arrête la ferme et persiste l'état. `{ "ok": true }` ou `{ "error": "..." }`.

#### `GET /api/farm/status`
Status détaillé : `running`, `cfg`, `started` (epoch), `accounts[]` (compte, `score`,
`label`, `followers`, `growth`, `active_days`, `tweets_ok`, `tweets_flagged`,
`done` par type, `status`), `log` (300 dernières actions simulées), **`run`**
(progression : `duration_days`, `day_index`, `left_days`, `ends_at`, `completed`).

#### `GET /api/farm/scores`
Tableau de scores compact (champs de `status.accounts`, dont `eta_days` /
`eta_note` — estimation calendaire du temps restant jusqu'à `ready ≥ 70`,
projetée à partir des taux observés : followers/jour mesuré, jours actifs au
rythme du profil courant, visibilité supposée constante ; `eta_note` porte le
blocage quand l'ETA est incalculable : `compromised`, `posts hidden`,
`no follower growth`, `trajectory too weak`). Voir `estimate_ready_days` dans
`xbot/farm.py`.

#### `POST /api/farm/generate`
Génère du contenu de vie **pour revue navigateur** — n'écrit rien dans l'espace
user (l'user fusionne dans la zone de texte puis clique
« Save content »).

```json
{ "channel": "users", "lang": "fr" }
```
- `channel` ∈ `users` (30 handles mainstream depuis `farm_content.USERS_BANK`) |
  `posts` (20 gabarits spintax bruts FR/EN — `lang` ∈ `fr` (défaut) | `en`) |
  `tweet_ids` (IDs de tweets récents récupérés en direct sur la timeline
  publique de syndication de très gros comptes — `502` si indisponible).
- Réponse : `{ "ok": true, "lines": [...] }`.

---

### Admin (droits administrateur requis)

#### `GET /api/admin/users`
```json
{ "users": [
  { "username": "boss", "is_admin": true, "accounts": 0, "running": false },
  { "username": "client1", "is_admin": false, "accounts": 50, "running": true }
] }
```

#### `POST /api/admin/users`
```json
{ "username": "client2", "password": "secret123", "is_admin": false }
```
Réponse `{ "ok": true }` ou `400 { "error": "cet user existe déjà" }`.

#### `DELETE /api/admin/users/<name>`
Supprime l'user (impossible sur soi-même). `{ "ok": true }`.

#### `POST /api/admin/users/<name>/password`
```json
{ "password": "nouveau123" }
```

#### `GET /api/admin/users/<name>/detail`
Config, fichiers et historique persistant (500 dernières lignes) d'un user.
```json
{
  "config": { "...": "..." },
  "files": { "accounts.txt": "...", "users.txt": "...", "...": "..." },
  "history": [ { "t": 1718.., "ok": true, "action": "Like", "msg": "@bob liked 123" } ],
  "live": { "running": false, "...": "..." }
}
```

---

### Divers

#### `GET /`
Health check (pas d'auth). `{ "service": "x-automation-api", "ok": true }`

#### `OPTIONS *`
Preflight CORS, renvoie les en-têtes `Access-Control-Allow-*`.

---

## Format des fichiers

Tous éditables via `POST /api/file/<name>`.

| File | Format | Exemple |
|---------|--------|---------|
| `accounts.txt` | une ligne par compte `username:…:auth_token` | `bob:xxx:abcdef123...` |
| `users.txt` | un username par ligne (sans `@`), pour les mentions | `elonmusk` |
| `tweets.txt` | tableau JSON d'objets `{"text": "..."}` | `[{"text":"gm"}]` |
| `reply.txt` | tableau JSON d'objets `{"text": "..."}` | `[{"text":"nice"}]` |
| `tweet_ids.txt` | un ID de tweet par ligne | `1899999999999999999` |
| `dms.txt` | tableau JSON d'objets `{"text": "..."}`, messages privés (action 13) | `[{"text":"salut"}]` |

> Le username est lu via `split(":")[0]` et le token via `split(":")[-1]` : tout ce qui est au milieu (mot de passe, email…) est ignoré par le runner.

---

## Configuration (par user)

Stockée dans `data/<user>/config.json`. Champs et valeurs par défaut :

| Clé | Défaut | Description |
|-----|--------|-------------|
| `proxy` | `""` | Proxy **de repli / partagé** `user:pass@host:port` (vide = connexion directe) |
| `proxies` | `""` | Liste de proxies (un par ligne). Le compte N de `accounts.txt` utilise la ligne N ; les comptes sans ligne passent par `proxy` (repli). Schémas : `http(s)://`, `socks5(h)://` — HTTP par défaut |
| `proxy_mode` | `"static"` | `"static"` : chaque ligne utilisée telle quelle (résidentiel dédié / datacenter). `"rotating"` : gateway résidentielle « backconnect » — le bot épingle une **session sticky par compte** (suffixe `-session-<id>` ajouté au username) pour que chaque compte garde une IP de sortie stable malgré la rotation de la gateway ; les lignes contenant déjà `-session-` sont utilisées telles quelles (syntaxe fournisseur manuelle possible) |
| `proxy_session_epoch` | `0` | Compteur de rotation des sessions épinglées. `POST /api/proxy/rotate-sessions` l'incrémente → nouvelles IP de sortie par compte |

Garanties d'IP en mode `rotating` : chaque compte garde **la même session donc
la même IP de sortie pour toutes ses requêtes, dans le temps** (distincte des
autres comptes), jusqu'à rotation explicite. Limite : la gateway garde la
session selon sa propre TTL (souvent tant qu'il y a du trafic + quelques
minutes) — une IP fixe « à vie » par compte exige des proxies résidentiels
**statiques** (une ligne par compte, mode `static`).
| `threads` | `5` | Nombre de comptes traités en parallèle |
| `limit` | `1` | Répétitions de l'action par compte |
| `select_users` | `1` | Nb de mentions piochées par post (Quote Tweet) |
| `mentions_per_target` | `1` | Nb max de comptes mentionnant une même cible ; les cibles de `users.txt` sont réparties entre les comptes (anti-spam) |
| `follow_mentioned` | `0` | Suivre chaque cible avant de la mentionner (augmente la probabilité de notification) |
| `random_mention_position` | `1` | Place les @mentions aléatoirement en début ou fin de message (cassage de pattern) |
| `delay_min` / `delay_max` | `1` / `3` | Délai aléatoire (s) entre deux actions |
| `account_delay_min` / `account_delay_max` | `10` / `25` | Délai (s) entre deux répétitions si `limit > 1` |
| `pfp_image` | `"pfp.jpg"` | Nom du fichier image pour la photo de profil |
| `display_name` | `""` | Nom d'affichage (action 9) |
| `bio` | `""` | Bio (action 9) |

---

## Les actions (1–13)

| `action_mode` | Nom | Files / config requis |
|:---:|------|--------------------------|
| 1 | Quote Tweet | `tweets.txt` + `users.txt` non vides ; `select_users`, `mentions_per_target`, `random_mention_position` |
| 2 | Retweet | `tweet_ids.txt` non vide |
| 3 | Like | `tweet_ids.txt` non vide |
| 4 | Reply | `tweet_ids.txt` + `reply.txt` non vides |
| 5 | View Tweet | `tweet_ids.txt` non vide |
| 6 | Bookmark | `tweet_ids.txt` non vide |
| 7 | Cross Follow | (chaque compte suit tous les autres de `accounts.txt`) |
| 8 | Change PFP | l'image `pfp_image` doit exister |
| 9 | Change Name/Bio | `display_name` et/ou `bio` renseigné |
| 10 | Check Premium | (lecture seule sur les comptes du fichier) |
| 11 | Publish Article | `articles.json` (⚠️ queryId non requis — indisponible) |
| 12 | Follow Target | `users.txt` non vide ; cibles réparties comme l'action 1 (`mentions_per_target`) |
| 13 | Send DM | `users.txt` + `dms.txt` non vides ; cibles réparties comme l'action 1 |

`accounts.txt` non vide est requis pour **toutes** les actions. Les actions 7, 8, 9, 10, 11, 12 et 13 ne s'exécutent qu'une fois par compte (`limit` ignoré).

**Canaux de notification directs (actions 12 et 13) :** la mention (action 1) est
filtrée par le « quality filter » de X quand le compte émetteur est low-reputation.
Deux canaux alternatifs touchent le téléphone de la cible :

- **Action 12 (Follow Target)** — la notif « X vous suit » est poussée par défaut
  sur mobile. Le message voyage dans le **nom affiché** (préparer l'action 9) et la
  **photo de profil** (action 8) : la cible lit *« [votre message] vous suit »*.
- **Action 13 (Send DM)** — le message d'un inconnu arrive en **« demande de
  message »**, ce qui déclenche une notif même sans relation existante.
  Résolution `@cible → user_id` via `UserByScreenName` (refactor `check_premium`
  en `_lookup_user` partagé), envoi par `dm/new2.json`.

⚠️ Limites : aucune de ces actions ne **garantit** la réception côté mobile (réglages
de la cible, quality filter). Un compte flagué qui enchaîne les follows/DM est vite
locké. Contrairement aux posts, les follows/DM ne fournissent pas de signal de
visibilité — le succès = requête acceptée, la réception réelle reste invérifiable.
Warm-up obligatoire (PFP, bio, activité organique) avant toute campagne.

**Détection des tweets masqués (actions 1 et 4) :** X ne renvoie pas d'erreur quand
il flague un tweet comme spam — le tweet est créé mais invisible pour les autres
(et les mentions ne notifient pas). Le runner inspecte le `__typename` du résultat
(`TweetWithVisibilityResults`, tombstone) : un post restreint est comptabilisé dans
le compteur `hidden` de `/api/status` (et dans le journal en rouge), pas dans `success`.

**Répartition des cibles (actions 1, 12, 13) :** `users.txt` alimente une **file
partagée** (`TargetPool`, thread-safe) — chaque cible y apparaît `mentions_per_target`
fois, mélangée, et n'est consommée qu'une fois globalement. Les comptes tirent leurs
cibles à la volée : un compte qui échoue (auth, proxy mort) **ne consomme rien** et les
comptes suivants prennent les cibles restantes à sa place — une cible n'est jamais
perdue avec un compte mort. Quand la file est épuisée, les comptes restants consignent
« no target available (shared target pool exhausted) » et s'arrêtent.

---

## Farm (réchauffement autonome)

Objectif : laisser des comptes « dormir » sur le serveur pendant que le moteur les fait
« vivre » — actions banales anti-heuristique à cadence humaine — jusqu'à ce qu'un
**score d'humanisation mesuré** certifie qu'ils passent les filtres (aptitude aux
campagnes mentions/DM).

Le contenu de vie (`users.txt`, `tweet_ids.txt`, `tweets.txt`) s'édite directement
depuis l'onglet **Farm** du panneau web (carte « Life content »), via
`GET/POST /api/file/<name>` — pas besoin d'accès au système de fichiers.
Chaque champ a un bouton **Generate** (`POST /api/farm/generate`, module
`xbot/farm_content.py`) : banque de comptes mainstream, gabarits spintax FR/EN,
et IDs de tweets viraux récupérés en direct (syndication, sans auth). Chaque
canal est optionnel tant qu'au moins un des trois est rempli au démarrage.

### Moteur (`xbot/farm.py`)

- `FarmRunner` : une par user (registre `farms` dans `context.py`), thread
  daemon unique, tick toutes les **45–75 s** (jitter).
- Chaque jour, pour CHAQUE COMPTE, `generate_plan` produit un **plan d'actions
  horodatées** : répartition uniforme sur 24 h ; counts exacts par action ; facteur
  de variation aléatoire par compte et par jour dans `[variation_min, variation_max]%`
  (garde-fou ≥ 1 action/jour quand la config globale > 0).
- **Durée (`run`)** : si `now ≥ run.start + duration_days × 86400`, le tick marque
  `run.completed = true`, passe `engine.reason = "completed"`, arrête la boucle
  (`stop_event`) et persiste `running = false`. Le panneau affiche alors "completed"
  avec progression `day_index / duration_days` via `GET /api/farm/status` (`run`
  = `{ duration_days, day_index, left_days, ends_at, completed }`).
- **Cibles sans répétition** : à la génération du plan, chaque cible (handle,
  tweet-id ou texte organique) est tirée SANS remise dans `used[account][kind]`
  (persisté dans `farm_state.json`, réinitialisé à chaque `start`). Pools épuisées
  → les kinds concernés sont consignés dans le plan log (`pool exhausted: ...`).
- Actions simulées (aucune mention, aucun DM, aucune rafale, **≤ 1 action/compte/tick**) :
  - `follow` — `users.txt` (moins les comptes de la ferme, anti auto-suivi)
  - `like` / `retweet` / `bookmark` / `view` — `tweet_ids.txt` (posts viraux)
  - `tweet` — `tweets.txt` avec mutation anti-signature (`{a|b}` spintax + emoji + ponctuation)
- Pas de contenu → l'action est absente du plan (les autres actions conservent leur count).
- Tweets de la ferme passent par le pipeline de **détection de visibilité** déjà en place
  (`TweetWithVisibilityResults` / tombstone) — chaque post est enregistré dans `vis`.
- 1 lecture `UserByScreenName` / jour / compte (étalée) → mesure `followers_organiques`.
- Proxy : la ferme résout le proxy **par compte** via `proxies.txt`/`config.proxies`
  (ligne N ↔ compte N), en épinglant une session sticky par compte en mode `rotating`.
- Anti double-débit : `/api/run` renvoie `409` si la ferme tourne, et
  `/api/farm/start` renvoie `409` si un job manuel tourne.
- Status persistant dans `farm_state.json` : reprise après restart du service.
  Au premier tick post-redémarrage (`maybe_resume`), un run expiré est finalisé
  (`completed`) et la boucle s'arrête proprement.

### Score d'humanisation (0 – 100), mesuré sur des faits

| Composant | Poids | Mesure |
|---|---:|---|
| Visibilité des tweets | 40 | % des tweets récents **non masqués** (fenêtre glissante 50) |
| Croissance organique | 20 | `followers − followers_à_linstallation`, objectif 50 |
| Profondeur d'activité | 20 | jours distincts avec action réussie, objectif 14 |
| Profile prêt | 10 | nom + bio + photo configurés (prérequis actions 8/9) |
| Intégrité | 10 | pas d'échec d'auth en rafale (3 failed conso ou récents) |

Labels : `dormant` < 30 ≤ `warming` < 70 ≤ `ready` ; `compromised` si 3 failed d'auth
d'affilée. **Un compte n'est « ready » que s'il a prouvé** (pas seulement vieilli)
que X ne filtre plus ses posts — c'est le prérequis aux campagnes mentions/DM.

### Points techniques importants

- Plans persistés par jour dans `farm_state.json` → reprise après restart du service.
- ≤ 1 action par compte par tick (~1 min) ; répartition sur 24 h ; chaque compte
  agit chaque jour (pas de jours de repos).
- Follows : pool `users.txt` moins les comptes de la ferme (anti auto-suivi entre bots).
- Anti double-débit : `/api/run` → 409 si la ferme tourne ; `/api/farm/start` → 409 si manuel.
- **Télémétrie moteur** (`status()` → `engine`) : à chaque tick la ferme publie
  `last_tick` (heartbeat), `planned`/`done`/`pending`/`failed` du jour, `next_due`
  (timestamp de la prochaine action) et `reason` (`waiting` / `plan_exhausted` /
  `no_content` / `no_accounts` / `no_active_accounts` / **`completed`** pour les fins
  de run). Le panneau l'affiche sous « Status » — c'est la preuve de vie et la
  réponse à « pourquoi ne se passe-t-il rien ? ». Les ticks du plan sont journalisés
  (`plan YYYY-MM-DD: N actions across M accounts`, avec suffixe `pool exhausted:`
  le cas échéant) et toutes les 30 min de silence
  apparaît un message `engine alive` (uniquement compteurs/minutes — jamais de cibles,
  IP, tokens ou erreurs internes).
- Proxy : résolution **par compte** (`config.proxies`, ligne ↔ compte, repli sur
  `config.proxy`), identique pour la ferme, les jobs manuels et le scraping. En mode
  `rotating`, une session sticky par compte est épinglée (`-session-` dans le username)
  et `POST /api/proxy/rotate-sessions` régénère toutes les sessions (nouvelles IP).
  Un échec réseau/proxy pendant l'auth ne dégrade PAS la santé du compte
  (`last_net_error` → détail « proxy/network error », pas de compteur d'échec auth).
- L'échec d'auth ×3 (rafale ou cumul 24 h) retire le compte de la ferme (`compromised`).

---

## Organisation des données

```
data/
├── users.json          # { "username": { "password_hash": "...", "is_admin": bool } }
├── .secret_key         # clé de signature des tokens (généré auto)
└── <username>/
    ├── config.json
    ├── accounts.txt
    ├── users.txt
    ├── dms.txt
    ├── tweets.txt
    ├── reply.txt
    ├── tweet_ids.txt
    ├── pfp.jpg          # uploadée via /api/upload-pfp
    ├── history.log      # 1 ligne JSON par action (historique persistant)
    └── farm_state.json  # état de la ferme : plans, compteurs, followers, score
```

Chaque user est totalement isolé : un user ne peut accéder qu'à son propre dossier via l'API. Seul un admin peut consulter les données d'autrui (lecture seule via `/api/admin/.../detail`).

---

## Déploiement

Le serveur Flask intégré ne convient pas à la production. Utiliser un serveur WSGI :

```bash
pip install gunicorn
export FRONTEND_ORIGIN="https://mon-front.com"   # verrouille le CORS
gunicorn -c gunicorn.conf.py run:app
```

Placer derrière un reverse proxy (nginx) avec **HTTPS**.

### Variables d'environnement

| Variable | Défaut | Role |
|----------|--------|------|
| `FRONTEND_ORIGIN` | `*` | Origine autorisée pour le CORS |
| `XPFF_BASE_KEY` | (clé par défaut dans `config.py`) | Clé de dérivation du header `x-xp-forwarded-for` |

### Scaler sur plusieurs instances

`gunicorn -w N` lance N workers : les jobs et l'état live (`/api/status`) sont **en mémoire par processus**. Un même user doit donc toujours tomber sur le même worker, ou il faut une instance unique. Pour partager les tokens entre plusieurs machines, copier le **même `data/.secret_key`** partout.

---

## Sécurité

- **HTTPS obligatoire** : le token transite dans l'en-tête `Authorization`, en clair sans TLS.
- **`FRONTEND_ORIGIN`** : mettre l'URL exacte du front en prod (pas `*`).
- **`data/.secret_key`** : à sauvegarder et garder secret. Sa perte invalide tous les tokens.
- **Pas d'inscription publique** : création de comptes réservée au CLI et aux admins.
- **Anti path-traversal** : noms de fichiers en liste blanche ; nom de PFP forcé via `os.path.basename`.
- **Mots de passe** : hashés via `werkzeug.security` (jamais stockés en clair).
- Un admin ne peut pas supprimer son propre compte (évite de se verrouiller dehors).
```
