"""Ends the web installer after a long time without use.

The installer script waits as long as the web installer runs, and stops when it is gone.
"""

import os
import signal
import threading
import time

IDLE_LIMIT = 2 * 3600
CHECK_INTERVAL = 60


class IdleWatch:
    def __init__(self, limit=IDLE_LIMIT):
        self.limit = limit
        self.last = time.monotonic()

    def touch(self):
        self.last = time.monotonic()

    def expired(self, now=None):
        return (time.monotonic() if now is None else now) - self.last >= self.limit

    def start(self):
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        while not self.expired():
            time.sleep(CHECK_INTERVAL)
        # Shown by the script, which prints the container log when the web installer is gone.
        print(f"Der Web-Installer wurde {self.limit // 3600} Stunden nicht benutzt und beendet sich.", flush=True)
        os.kill(os.getpid(), signal.SIGTERM)
