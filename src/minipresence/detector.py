from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from ctypes import wintypes
from dataclasses import dataclass
from functools import lru_cache

import psutil

PWA_ID_PATTERN = re.compile(r"--app-id(?:=|\s+)([a-z0-9_-]+)", re.IGNORECASE)
BROWSER_NAMES = {
    "Edge": {"msedge.exe", "msedge"},
    "Chrome": {"chrome.exe", "chrome"},
}
PROCESS_DISPLAY_NAMES = {
    "chrome.exe": "Google Chrome",
    "code.exe": "Visual Studio Code",
    "discord.exe": "Discord",
    "discordcanary.exe": "Discord Canary",
    "excel.exe": "Microsoft Excel",
    "explorer.exe": "File Explorer",
    "firefox.exe": "Mozilla Firefox",
    "msedge.exe": "Microsoft Edge",
    "notepad.exe": "Notepad",
    "obs64.exe": "OBS Studio",
    "powerpnt.exe": "Microsoft PowerPoint",
    "slack.exe": "Slack",
    "spotify.exe": "Spotify",
    "steam.exe": "Steam",
    "teams.exe": "Microsoft Teams",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "winword.exe": "Microsoft Word",
}
IGNORED_PROCESS_NAMES = {
    "applicationframehost.exe",
    "dwm.exe",
    "lockapp.exe",
    "minipresence.exe",
    "searchhost.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "textinputhost.exe",
}
IGNORED_WINDOW_TITLES = {"Default IME", "MSCTFIME UI", "Program Manager"}


@dataclass(frozen=True, slots=True)
class DetectedWebApp:
    app_id: str
    browser: str
    process_name: str


@dataclass(frozen=True, slots=True)
class WebAppChoice:
    name: str
    app_id: str
    browser: str


@dataclass(frozen=True, slots=True)
class AppChoice:
    name: str
    target_type: str
    identifier: str
    type_label: str
    browser: str = "Any"


SHORTCUT_DISCOVERY_SCRIPT = r"""
$ShortcutShell = New-Object -ComObject WScript.Shell
$ShortcutRoots = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:USERPROFILE\Desktop",
    "$env:PUBLIC\Desktop"
)
$Apps = foreach ($ShortcutRoot in $ShortcutRoots) {
    if (-not (Test-Path -LiteralPath $ShortcutRoot)) { continue }
    $ShortcutFiles = Get-ChildItem -LiteralPath $ShortcutRoot -Filter '*.lnk' -Recurse `
        -ErrorAction SilentlyContinue
    $ShortcutFiles | ForEach-Object {
            $Shortcut = $ShortcutShell.CreateShortcut($_.FullName)
            if ($Shortcut.Arguments -match '--app-id[= ]([a-z0-9_-]+)') {
                $TargetName = [IO.Path]::GetFileName($Shortcut.TargetPath).ToLowerInvariant()
                $Browser = if ($TargetName -like '*edge*') {
                    'Edge'
                } elseif ($TargetName -like '*chrome*') {
                    'Chrome'
                } else {
                    $null
                }
                if ($Browser) {
                    [PSCustomObject]@{
                        name = $_.BaseName
                        app_id = $Matches[1]
                        browser = $Browser
                    }
                }
            }
        }
}
ConvertTo-Json -InputObject @($Apps) -Compress
"""


def extract_pwa_app_id(command_line: Sequence[str] | str) -> str | None:
    command = command_line if isinstance(command_line, str) else " ".join(command_line)
    match = PWA_ID_PATTERN.search(command)
    return match.group(1) if match else None


def browser_for_process(process_name: str) -> str | None:
    lowered = process_name.lower()
    for browser, names in BROWSER_NAMES.items():
        if lowered in names:
            return browser
    return None


def discover_web_apps(
    processes: Iterable[Mapping[str, object]] | None = None,
) -> list[DetectedWebApp]:
    if processes is None:
        processes = (proc.info for proc in psutil.process_iter(["name", "cmdline"]))

    found: dict[tuple[str, str], DetectedWebApp] = {}
    for process in processes:
        try:
            process_name = str(process.get("name") or "")
            browser = browser_for_process(process_name)
            if not browser:
                continue
            command_line = process.get("cmdline") or []
            if not isinstance(command_line, (str, list, tuple)):
                continue
            app_id = extract_pwa_app_id(command_line)
            if app_id:
                found[(browser, app_id)] = DetectedWebApp(app_id, browser, process_name)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return sorted(found.values(), key=lambda item: (item.browser, item.app_id))


def choices_from_shortcut_json(raw: str) -> list[WebAppChoice]:
    try:
        records = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(records, list):
        records = [records]

    found: dict[tuple[str, str], WebAppChoice] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        name = str(record.get("name") or "").strip()
        app_id = str(record.get("app_id") or "").strip()
        browser = str(record.get("browser") or "").strip()
        if name and app_id and browser in BROWSER_NAMES:
            found[(browser, app_id)] = WebAppChoice(name, app_id, browser)
    return sorted(found.values(), key=lambda item: item.name.casefold())


@lru_cache(maxsize=1)
def _cached_installed_web_apps() -> tuple[WebAppChoice, ...]:
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                SHORTCUT_DISCOVERY_SCRIPT,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    return tuple(choices_from_shortcut_json(completed.stdout))


def discover_installed_web_apps() -> list[WebAppChoice]:
    """Return a copy of the cached installed-PWA list for this MiniPresence session."""
    return list(_cached_installed_web_apps())


def match_running_web_apps(
    running_apps: Iterable[DetectedWebApp], installed_apps: Iterable[WebAppChoice]
) -> list[WebAppChoice]:
    installed = list(installed_apps)
    found = {(item.browser, item.app_id): item for item in installed}
    choices: list[WebAppChoice] = []
    unknown_counts: dict[str, int] = {}
    for running in running_apps:
        key = (running.browser, running.app_id)
        if key in found:
            choices.append(found[key])
            continue
        unknown_counts[running.browser] = unknown_counts.get(running.browser, 0) + 1
        suffix = unknown_counts[running.browser]
        name = f"{running.browser} web app"
        if suffix > 1:
            name = f"{name} {suffix}"
        choices.append(WebAppChoice(name, running.app_id, running.browser))
    return sorted(choices, key=lambda item: item.name.casefold())


def available_web_apps() -> list[WebAppChoice]:
    return match_running_web_apps(discover_web_apps(), discover_installed_web_apps())


def _visible_window_records() -> list[dict[str, object]]:
    if sys.platform != "win32":
        return []

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    records: list[dict[str, object]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    @callback_type
    def collect(window: int, _parameter: int) -> bool:
        if not user32.IsWindowVisible(window):
            return True
        length = user32.GetWindowTextLengthW(window)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(window, buffer, length + 1)
        title = buffer.value.strip()
        if not title or title in IGNORED_WINDOW_TITLES:
            return True

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
        if process_id.value == os.getpid():
            return True
        try:
            process_name = psutil.Process(process_id.value).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return True
        records.append({"title": title, "process_name": process_name})
        return True

    user32.EnumWindows(collect, 0)
    return records


def choices_from_window_records(records: Iterable[Mapping[str, object]]) -> list[AppChoice]:
    found: dict[str, AppChoice] = {}
    for record in records:
        title = str(record.get("title") or "").strip()
        process_name = str(record.get("process_name") or "").strip().lower()
        if (
            not title
            or not process_name
            or title in IGNORED_WINDOW_TITLES
            or process_name in IGNORED_PROCESS_NAMES
        ):
            continue
        name = PROCESS_DISPLAY_NAMES.get(process_name, title)
        if len(name) > 64:
            name = f"{name[:61]}..."
        found.setdefault(
            process_name,
            AppChoice(name, "process", process_name, "Desktop app"),
        )
    return sorted(found.values(), key=lambda item: item.name.casefold())


def available_apps() -> list[AppChoice]:
    web_apps = [
        AppChoice(item.name, "pwa", item.app_id, f"{item.browser} web app", item.browser)
        for item in available_web_apps()
    ]
    desktop_apps = choices_from_window_records(_visible_window_records())
    return sorted([*web_apps, *desktop_apps], key=lambda item: item.name.casefold())


def is_web_app_running(app_id: str, browser: str = "Any") -> bool:
    wanted = app_id.strip().lower()
    return any(
        item.app_id.lower() == wanted and (browser == "Any" or item.browser == browser)
        for item in discover_web_apps()
    )


def is_process_running(process_name: str) -> bool:
    wanted = process_name.strip().lower()
    if not wanted:
        return False
    for process in psutil.process_iter(["name"]):
        try:
            if str(process.info.get("name") or "").lower() == wanted:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False
