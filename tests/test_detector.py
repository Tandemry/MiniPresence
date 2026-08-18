from types import SimpleNamespace

import minipresence.detector as detector
from minipresence.detector import (
    AppChoice,
    DetectedWebApp,
    WebAppChoice,
    browser_for_process,
    choices_from_shortcut_json,
    choices_from_window_records,
    discover_installed_web_apps,
    discover_web_apps,
    extract_pwa_app_id,
    is_process_foreground,
    is_web_app_foreground,
    match_running_web_apps,
)


def test_extracts_equals_style_app_id():
    assert extract_pwa_app_id(["msedge.exe", "--app-id=abcdefghijklmnop"]) == "abcdefghijklmnop"


def test_extracts_separate_argument_app_id():
    assert extract_pwa_app_id("chrome.exe --app-id abc123") == "abc123"


def test_recognizes_supported_browsers():
    assert browser_for_process("msedge.exe") == "Edge"
    assert browser_for_process("CHROME.EXE") == "Chrome"
    assert browser_for_process("firefox.exe") is None


def test_discovers_unique_web_apps():
    processes = [
        {"name": "msedge.exe", "cmdline": ["msedge.exe", "--app-id=edge123"]},
        {"name": "msedge.exe", "cmdline": ["msedge.exe", "--app-id=edge123"]},
        {"name": "chrome.exe", "cmdline": ["chrome.exe", "--app-id=chrome123"]},
        {"name": "other.exe", "cmdline": ["other.exe", "--app-id=nope"]},
    ]
    apps = discover_web_apps(processes)
    assert [(app.browser, app.app_id) for app in apps] == [
        ("Chrome", "chrome123"),
        ("Edge", "edge123"),
    ]


def test_shortcuts_become_friendly_choices_without_exposing_ids():
    raw = """[
      {"name":"Volute Dashboard","app_id":"abc123","browser":"Chrome"},
      {"name":"My Portal","app_id":"edge123","browser":"Edge"}
    ]"""
    choices = choices_from_shortcut_json(raw)
    assert [(item.name, item.browser) for item in choices] == [
        ("My Portal", "Edge"),
        ("Volute Dashboard", "Chrome"),
    ]


def test_invalid_shortcut_output_is_ignored():
    assert choices_from_shortcut_json("not json") == []


def test_only_currently_running_apps_are_offered():
    installed = [
        WebAppChoice("Open App", "running123", "Chrome"),
        WebAppChoice("Closed App", "closed123", "Chrome"),
    ]
    running = [DetectedWebApp("running123", "Chrome", "chrome.exe")]
    assert match_running_web_apps(running, installed) == [
        WebAppChoice("Open App", "running123", "Chrome")
    ]


def test_open_windows_become_desktop_app_choices():
    records = [
        {"title": "Untitled - Notepad", "process_name": "notepad.exe"},
        {"title": "Project - Acme Editor", "process_name": "acme.exe"},
        {"title": "Second window", "process_name": "acme.exe"},
        {"title": "Program Manager", "process_name": "explorer.exe"},
        {"title": "MiniPresence", "process_name": "minipresence.exe"},
    ]
    assert choices_from_window_records(records) == [
        AppChoice("Notepad", "process", "notepad.exe", "Desktop app"),
        AppChoice("Project - Acme Editor", "process", "acme.exe", "Desktop app"),
    ]


def test_installed_web_app_discovery_is_cached_and_returns_copies(monkeypatch):
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            returncode=0,
            stdout='[{"name":"Portal","app_id":"abc","browser":"Edge"}]',
        )

    detector._cached_installed_web_apps.cache_clear()
    monkeypatch.setattr(detector.subprocess, "run", fake_run)
    try:
        first = discover_installed_web_apps()
        first.clear()
        second = discover_installed_web_apps()
        assert calls == 1
        assert second == [WebAppChoice("Portal", "abc", "Edge")]
    finally:
        detector._cached_installed_web_apps.cache_clear()


def test_desktop_presence_only_matches_the_foreground_process(monkeypatch):
    monkeypatch.setattr(
        detector,
        "_foreground_window_record",
        lambda: {"process_name": "notepad.exe", "title": "Notes"},
    )
    assert is_process_foreground("NOTEPAD.EXE")
    assert not is_process_foreground("spotify.exe")


def test_minimized_or_missing_foreground_window_is_inactive(monkeypatch):
    monkeypatch.setattr(detector, "_foreground_window_record", lambda: None)
    assert not is_process_foreground("notepad.exe")
    assert not is_web_app_foreground("abc123", "Edge", "Portal")


def test_web_app_foreground_matches_windows_app_identity(monkeypatch):
    monkeypatch.setattr(
        detector,
        "_foreground_window_record",
        lambda: {
            "process_name": "msedge.exe",
            "title": "Dashboard",
            "command_line": ["msedge.exe"],
            "app_user_model_id": "MSEdge._crx_abc123",
        },
    )
    assert is_web_app_foreground("abc123", "Edge", "Portal")
    assert not is_web_app_foreground("different", "Edge", "Portal")


def test_web_app_foreground_uses_command_line_or_title_fallback(monkeypatch):
    record = {
        "process_name": "chrome.exe",
        "title": "Volute Dashboard",
        "command_line": ["chrome.exe", "--app-id=volute123"],
        "app_user_model_id": "",
    }
    monkeypatch.setattr(detector, "_foreground_window_record", lambda: record)
    assert is_web_app_foreground("volute123", "Chrome", "Other name")

    record["command_line"] = ["chrome.exe"]
    assert is_web_app_foreground("volute123", "Chrome", "Volute Dashboard")
    assert not is_web_app_foreground("volute123", "Edge", "Volute Dashboard")
