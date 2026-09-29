# Login Tester

Ouvre un navigateur connecté à un compte X à partir de son `auth_token`.

## Installation (une fois)

```bash
pip install playwright
playwright install chromium
```

## Utilisation

```bash
# token en argument
python login_with_token.py 1a2b3c...votretoken

# ou saisie interactive
python login_with_token.py

# avec un proxy (recommandé : la même IP que d'habitude pour ce compte)
python login_with_token.py <auth_token> --proxy user:pass@host:port

# sans fenêtre (juste tester la validité)
python login_with_token.py <auth_token> --headless
```

## Ce que ça fait

1. Lance Chromium (fenêtre visible par défaut).
2. Injecte le cookie `auth_token` pour `x.com` / `twitter.com`.
3. Ouvre `x.com/home` → tu es connecté au compte.
4. Indique `✅ Logged in` ou `⚠️ logged OUT` (token invalide/expiré).
5. Laisse la fenêtre ouverte jusqu'à ce que tu appuies sur Entrée.

## Où trouver l'auth_token

C'est la 3ᵉ/dernière valeur des lignes de `accounts.txt` (`username:...:auth_token`),
ou le cookie `auth_token` d'une vraie session x.com (DevTools → Application → Cookies).

> [!note]
> Outil autonome, sans lien avec le panel. Utile pour vérifier un token, ou
> reprendre la main sur un compte manuellement. Utilise de préférence le proxy
> associé au compte pour éviter une alerte « nouvelle connexion ».
