"""CLI standalone — lance le bot en console (sans le serveur web).

Lit la config et les fichiers depuis le dossier ./workspace.
Usage : python -m cli.run_cli   (ou: python cli/run_cli.py)
"""
import json
import os
import sys
import time

# Permet l'exécution directe (python cli/run_cli.py) en ajoutant la racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from cli.ui import ACTION_NAMES, CYAN, GREEN, RED, RESET, clear_and_refresh, ask_action, Stats
from xbot.runner import BotRunner
from xbot.settings import WORKSPACE_DIR


def main():
    action_mode = ask_action()
    action_name = ACTION_NAMES[action_mode]
    print(f"\n{GREEN}✓ Selected: {action_name}{RESET}\n")
    time.sleep(1)

    try:
        with open(os.path.join(WORKSPACE_DIR, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"{RED}❌ workspace/config.json not found{RESET}")
        sys.exit(1)

    runner = BotRunner()
    err = runner.start(action_mode, cfg, WORKSPACE_DIR)
    if err:
        print(f"{RED}❌ {err}{RESET}")
        sys.exit(1)

    # Affichage live en se basant sur le status du runner
    cli_stats = Stats(action_name)
    seen = 0
    while runner.is_running():
        st = runner.status()
        cli_stats.success = st.get("success", 0)
        cli_stats.failed = st.get("failed", 0)
        cli_stats.total = st.get("total", 0)
        cli_stats.accounts_done = st.get("accounts_done", 0)
        log = st.get("log", [])
        if len(log) > seen:
            clear_and_refresh(cli_stats)
            for entry in log[seen:]:
                color = GREEN if entry["ok"] else RED
                mark = "✓" if entry["ok"] else "✗"
                print(f"{color}{mark}{RESET} {entry['msg']}")
            seen = len(log)
        time.sleep(0.5)

    clear_and_refresh(cli_stats)
    print(f"\n{GREEN}✨ {action_name} completed!{RESET}\n")


if __name__ == "__main__":
    main()
