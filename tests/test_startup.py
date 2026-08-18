from pathlib import Path

from minipresence.startup import startup_command


def test_packaged_startup_command_runs_in_background():
    command = startup_command(Path(r"C:\Program Files\MiniPresence.exe"), frozen=True)
    assert command == '"C:\\Program Files\\MiniPresence.exe" --background'


def test_source_startup_command_uses_module():
    command = startup_command(Path(r"C:\Python\pythonw.exe"), frozen=False)
    assert command == '"C:\\Python\\pythonw.exe" -m minipresence --background'
