# Mise à jour de sécurité

## Application de la mise à jour

Utiliser Python 3.12, comme l'image Docker. Arrêter l'ancienne application avant
de migrer la base. Dans le dossier du projet :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe manage.py upgrade
.\.venv\Scripts\python.exe run.py
```

En production Linux, utiliser `gunicorn -c gunicorn.conf.py run:app`.
Le conteneur migre la base avec `manage.py upgrade` avant le démarrage.
Le démarrage SQLite migre également la base automatiquement. La migration
reconnaît les anciennes bases créées sans Alembic et conserve les comptes,
mots de passe et chemins des espaces existants. Une copie `.bak` de l'ancienne
base SQLite non versionnée est créée avant sa première migration.
Sauvegarder aussi les fichiers de `data/` ; PostgreSQL doit être sauvegardé
avant une migration en production.

Tous les utilisateurs, y compris l'administrateur, doivent se reconnecter :
les anciens jetons ne contiennent pas l'identité de l'espace utilisateur.

## Corrections

- Les historiques affichent les messages comme du texte échappé. Les scripts
  sont dans `/static` ; la CSP interdit les scripts et gestionnaires inline.
- Les articles importés sont reconstruits à partir d'une liste de balises de
  mise en forme autorisées. Les attributs dangereux et liens hors HTTP/HTTPS
  sont supprimés ; le collage se fait en texte brut.
- Les chemins sont confinés à l'espace utilisateur, y compris pour les photos
  de profil. Chemins absolus, traversées et liens vers d'autres fichiers sont
  rejetés. Le moteur utilise le chemin complet de la photo de l'utilisateur.
- Chaque nouveau compte reçoit une identité d'espace aléatoire. Une suppression
  révoque l'accès et arrête les tâches ; recréer le même nom crée un espace neuf.
  Les anciens fichiers sont conservés sur le serveur, sans accès depuis le
  nouveau compte. Aucune purge automatique des données n'est effectuée.
- Les modérateurs ne peuvent plus consulter les fichiers et secrets d'autrui.
  Les utilisateurs ordinaires n'ont accès qu'à leur espace.
- Les pauses sont interruptibles, les requêtes réseau ont un délai maximal et
  les comptes en attente ne sont plus tous soumis simultanément à l'exécuteur.
  Une requête déjà transmise à X peut se terminer après la demande d'arrêt ;
  elle ne peut pas être annulée à distance.
- Les erreurs présentes dans les réponses JSON de X ne sont plus comptées
  comme des succès simplement parce que le code HTTP est 200. Les échecs
  d'authentification et exceptions font avancer le compteur de comptes traités.
- Les corps JSON incorrects et dépassements de limites sont refusés ; l'interface
  affiche les erreurs d'enregistrement et ne lance pas une tâche après l'échec
  d'enregistrement de ses fichiers.
- La dépendance XClientTransaction pointe vers une version disponible sur PyPI ;
  l'import de Session et le profil navigateur correspondent à curl_cffi 0.7.4.

## Limites de ressources

Ces valeurs se règlent côté serveur dans `.env`, pas depuis le panneau utilisateur :

| Variable | Valeur par défaut |
| --- | --- |
| `MAX_THREADS_PER_USER` | 10 |
| `MAX_ACTIVE_JOBS` | 4 |
| `MAX_ACCOUNTS_PER_JOB` | 1000 |
| `X_REQUEST_TIMEOUT` | 20 secondes par requête |

Les configurations existantes dépassant la limite de threads doivent être
réduites avant de relancer une tâche. `BEHIND_PROXY=true` doit être explicite
si le service se trouve derrière un proxy de confiance ; ne pas exposer le
port applicatif directement dans cette configuration.

## Limites fonctionnelles restantes

Le scraping non configuré est refusé avant toute connexion à X. La publication
d'articles est désactivée car son protocole reste incomplet. Cette mise à jour
ne prétend pas valider les endpoints internes de X en conditions réelles.

Les tâches restent en mémoire : garder un seul processus Gunicorn et une seule
instance. Un redémarrage n'entraîne pas de reprise automatique des publications,
afin de ne pas répéter des actions dont le résultat précédent est inconnu.

## Vérification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests emploient des bases temporaires et des données fictives. Les requêtes
X sont bloquées. Le test de lien symbolique est ignoré si Windows n'autorise pas
sa création. `tests/browser-security.cjs` s'exécute avec Node et Playwright
disponibles dans `NODE_PATH` ; `BROWSER_EXECUTABLE` permet de choisir un navigateur
installé. Toutes ses réponses API sont simulées et aucune action X n'est envoyée.

Source de la dépendance corrigée : [XClientTransaction sur PyPI](https://pypi.org/project/xclienttransaction/).
