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
    app.run(host="0.0.0.0", port=5000, debug=debug, threaded=True)
