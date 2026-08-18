from __future__ import annotations

from typing import Any

from pypresence import Presence


class DiscordPresence:
    def __init__(self) -> None:
        self._client: Presence | None = None
        self._client_id: str | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    def connect(self, client_id: str) -> None:
        if self._client is not None and self._client_id == client_id:
            return
        self.close()
        client = Presence(client_id)
        client.connect()
        self._client = client
        self._client_id = client_id

    def update(self, payload: dict[str, Any]) -> None:
        if self._client is None:
            raise RuntimeError("Discord is not connected")
        self._client.update(**payload)

    def clear(self) -> None:
        if self._client is not None:
            self._client.clear()

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.clear()
            except Exception:
                pass
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._client_id = None
