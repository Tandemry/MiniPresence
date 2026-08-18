from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MiniPresence"


def startup_command(executable: Path, frozen: bool) -> str:
    if frozen:
        return f'"{executable}" --background'
    return f'"{executable}" -m minipresence --background'


def set_startup_enabled(enabled: bool) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            command = startup_command(Path(sys.executable), bool(getattr(sys, "frozen", False)))
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            configured_command, _value_type = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False
    expected_command = startup_command(
        Path(sys.executable),
        bool(getattr(sys, "frozen", False)),
    )
    return configured_command == expected_command
