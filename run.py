"""Point d'entrée de l'API.

Dev :        python run.py
Dev debug :  FLASK_DEBUG=1 python run.py   (reloader + debugger Werkzeug — JAMAIS en prod)
Prod :       gunicorn -c gunicorn.conf.py run:app
"""
import os

from xbot import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG") in ("1", "true", "on")
    port = int(os.getenv("PORT", "5000"))
    # `::` écoute en IPv6 ET en IPv4 (dual-stack Linux par défaut) : sans ça,
    # l'interface n'est joignable que par l'adresse IPv4 — inutilisable depuis
    # l'IPv6 Tailscale. Repli sur IPv4 si la pile IPv6 est désactivée.
    host = os.getenv("HOST", "::")
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except OSError:
        app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
