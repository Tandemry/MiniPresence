from __future__ import annotations

import threading
import time
from collections.abc import Callable

from minipresence.config import MINIPRESENCE_CLIENT_ID, Settings
from minipresence.detector import is_process_running, is_web_app_running
from minipresence.rpc import DiscordPresence

StatusCallback = Callable[[str, str], None]
PRESENCE_REFRESH_SECONDS = 15.0


def presence_update_due(
    active: bool,
    last_update: float,
    now: float,
    refresh_seconds: float = PRESENCE_REFRESH_SECONDS,
) -> bool:
    return not active or now - last_update >= refresh_seconds


class PresenceMonitor:
    def __init__(self, callback: StatusCallback) -> None:
        self._callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._rpc = DiscordPresence()
        self._last_status: tuple[str, str] | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: Settings) -> None:
        self.stop()
        self._stop_event.clear()
        self._last_status = None
        self._thread = threading.Thread(
            target=self._run, args=(settings,), name="presence-monitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._rpc.close()
        self._thread = None

    def _run(self, settings: Settings) -> None:
        active = False
        started_at = 0
        last_update = 0.0
        self._emit("watching", f"Waiting for {settings.app_name}")

        while not self._stop_event.is_set():
            try:
                if settings.target_type == "process":
                    detected = is_process_running(settings.process_name)
                else:
                    detected = is_web_app_running(settings.pwa_app_id, settings.browser)
                now = time.monotonic()
                if detected and presence_update_due(active, last_update, now):
                    if not started_at:
                        started_at = int(time.time())
                    self._rpc.connect(MINIPRESENCE_CLIENT_ID)
                    self._rpc.update(settings.presence_payload(started_at))
                    was_active = active
                    active = True
                    last_update = now
                    if not was_active:
                        self._emit("active", f"Presence active for {settings.app_name}")
                elif not detected and active:
                    self._rpc.clear()
                    active = False
                    started_at = 0
                    last_update = 0.0
                    self._emit("watching", f"Waiting for {settings.app_name}")
                elif not detected:
                    self._emit("watching", f"Waiting for {settings.app_name}")
            except Exception:
                active = False
                last_update = 0.0
                self._rpc.close()
                self._emit("error", "Discord isn't connected")

            self._stop_event.wait(settings.poll_seconds)

        self._rpc.close()
        self._emit("stopped", "Monitoring stopped")

    def _emit(self, status: str, message: str) -> None:
        current = (status, message)
        if current == self._last_status:
            return
        self._last_status = current
        self._callback(status, message)
