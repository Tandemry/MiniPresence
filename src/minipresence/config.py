from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME = "MiniPresence"
MINIPRESENCE_CLIENT_ID = "1539241245313073212"
KNOWN_APP_IMAGES = {
    "volute dashboard": "https://i.ibb.co/VcdVtnXk/Vol-Dashlogo1.png",
}


def default_config_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / APP_DIR_NAME / "config.json"


@dataclass(slots=True)
class Settings:
    app_name: str = "My App"
    target_type: str = "pwa"
    process_name: str = ""
    browser: str = "Any"
    pwa_app_id: str = ""
    details: str = "Using {app_name}"
    state: str = "App open"
    large_image: str = ""
    large_text: str = "{app_name}"
    poll_seconds: float = 3.0
    start_minimized: bool = False

    @property
    def has_target(self) -> bool:
        if self.target_type == "process":
            return bool(self.process_name.strip())
        return bool(self.pwa_app_id.strip())

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.app_name.strip():
            errors.append("App name is required.")
        if self.target_type not in {"process", "pwa"}:
            errors.append("App type is invalid.")
        elif not self.has_target:
            errors.append("Choose an app first.")
        if not 1 <= self.poll_seconds <= 60:
            errors.append("Check interval must be between 1 and 60 seconds.")
        return errors

    def presence_payload(self, started_at: int) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.app_name[:128],
            "details": self.details.replace("{app_name}", self.app_name)[:128],
            "state": self.state.replace("{app_name}", self.app_name)[:128],
            "start": started_at,
        }
        large_image = self.large_image.strip() or KNOWN_APP_IMAGES.get(
            self.app_name.strip().casefold(), ""
        )
        if large_image:
            payload["large_image"] = large_image
            payload["large_text"] = self.large_text.replace("{app_name}", self.app_name)[:128]
        return payload


def load_settings(path: Path | None = None) -> Settings:
    config_path = path or default_config_path()
    if not config_path.exists():
        return Settings()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    defaults = asdict(Settings())
    values: dict[str, object] = {}
    for key, default in defaults.items():
        value = raw.get(key, default)
        if isinstance(default, str) and isinstance(value, str):
            values[key] = value
        elif isinstance(default, bool) and isinstance(value, bool):
            values[key] = value
        elif (
            key == "poll_seconds"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            values[key] = float(value)
        else:
            values[key] = default
    settings = Settings(**values)
    if not 1 <= settings.poll_seconds <= 60:
        settings.poll_seconds = Settings().poll_seconds
    if settings.target_type not in {"process", "pwa"}:
        settings.target_type = "pwa"
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = config_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    temporary.replace(config_path)
    return config_path
