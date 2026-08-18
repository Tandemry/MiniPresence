import json

from minipresence.config import MINIPRESENCE_CLIENT_ID, Settings, load_settings, save_settings


def test_settings_round_trip(tmp_path):
    path = tmp_path / "config.json"
    original = Settings(app_name="Example", pwa_app_id="abc123")
    save_settings(original, path)
    assert load_settings(path) == original


def test_presence_payload_expands_app_name():
    settings = Settings(app_name="Example", pwa_app_id="abc", details="Using {app_name}")
    assert settings.presence_payload(10)["details"] == "Using Example"
    assert settings.presence_payload(10)["name"] == "Example"


def test_known_app_image_matching_ignores_surrounding_spaces():
    settings = Settings(app_name="  Volute Dashboard  ", pwa_app_id="abc")
    assert (
        settings.presence_payload(10)["large_image"]
        == "https://i.ibb.co/VcdVtnXk/Vol-Dashlogo1.png"
    )


def test_volute_dashboard_uses_its_public_icon_automatically():
    settings = Settings(app_name="Volute Dashboard", pwa_app_id="abc")
    payload = settings.presence_payload(10)
    assert payload["large_image"] == "https://i.ibb.co/VcdVtnXk/Vol-Dashlogo1.png"
    assert payload["large_text"] == "Volute Dashboard"


def test_custom_icon_overrides_known_app_icon():
    settings = Settings(
        app_name="Volute Dashboard",
        pwa_app_id="abc",
        large_image="https://example.com/custom.png",
    )
    assert settings.presence_payload(10)["large_image"] == "https://example.com/custom.png"


def test_validation_rejects_bad_values():
    settings = Settings(app_name="", pwa_app_id="", poll_seconds=0)
    assert len(settings.validate()) == 3


def test_desktop_app_is_a_valid_saved_target():
    settings = Settings(
        app_name="Notepad",
        target_type="process",
        process_name="notepad.exe",
    )
    assert settings.has_target
    assert settings.validate() == []


def test_old_client_id_is_ignored_during_migration(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"client_id": "", "app_name": "Example", "pwa_app_id": "abc123"}),
        encoding="utf-8",
    )
    assert load_settings(path) == Settings(app_name="Example", pwa_app_id="abc123")


def test_non_object_config_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[]", encoding="utf-8")
    assert load_settings(path) == Settings()


def test_invalid_config_types_are_safely_normalized(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "app_name": ["not", "text"],
                "poll_seconds": 999,
                "start_minimized": "yes",
            }
        ),
        encoding="utf-8",
    )
    assert load_settings(path) == Settings()


def test_shared_application_id_is_configured():
    assert MINIPRESENCE_CLIENT_ID == "1539241245313073212"
    assert MINIPRESENCE_CLIENT_ID.isdigit()
