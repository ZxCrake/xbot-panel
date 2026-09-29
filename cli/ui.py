import os
import time
from threading import Lock

CYAN   = "\033[1;36m"
GREEN  = "\033[1;32m"
RED    = "\033[1;31m"
YELLOW = "\033[1;33m"
PURPLE = "\033[1;35m"
WHITE  = "\033[1;37m"
GRAY   = "\033[1;30m"
RESET  = "\033[0m"

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
    12: "Follow Target",
    13: "Send DM",
}


class Stats:
    def __init__(self, action_name: str):
        self._lock = Lock()
        self.action_name = action_name
        self.total = 0
        self.success = 0
        self.failed = 0
        self.accounts_done = 0
        self.start_time = time.time()

    def record_ok(self):
        with self._lock:
            self.total += 1
            self.success += 1

    def record_fail(self):
        with self._lock:
            self.total += 1
            self.failed += 1

    def record_account_done(self):
        with self._lock:
            self.accounts_done += 1

    def render(self) -> str:
        elapsed_s = int(time.time() - self.start_time)
        elapsed = f"{elapsed_s // 60:02d}:{elapsed_s % 60:02d}"
        rate = (self.success / self.total * 100) if self.total else 0
        return (
            f"{CYAN}[{self.action_name}]{RESET}  "
            f"OK {GREEN}{self.success}{RESET}  "
            f"Fail {RED}{self.failed}{RESET}  "
            f"Total {self.total}  "
            f"Rate {rate:.0f}%  "
            f"Accounts {self.accounts_done}  "
            f"Time {elapsed}"
        )


def clear_and_refresh(stats: Stats):
    os.system("cls||clear")
    print(stats.render())
    print(f"{GRAY}{'-' * 60}{RESET}")


def ask_action() -> int:
    os.system("cls||clear")
    print(f"{CYAN}=== X Automation Tool ==={RESET}\n")
    for num, name in ACTION_NAMES.items():
        print(f"  {num}. {name}")
    print()
    while True:
        try:
            choice = input(f"{CYAN}Select action: {RESET}").strip()
            if choice.isdigit() and int(choice) in ACTION_NAMES:
                return int(choice)
            print(f"{RED}Invalid choice. Pick one from the list above.{RESET}")
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception:
            print(f"{RED}Invalid input.{RESET}")
