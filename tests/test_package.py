import re
from pathlib import Path

import minipresence


def test_package_versions_stay_in_sync():
    project_root = Path(__file__).resolve().parents[1]
    project_text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', project_text, re.MULTILINE)
    assert version is not None
    assert version.group(1) == minipresence.__version__


def test_required_visual_assets_are_packaged():
    asset_dir = Path(minipresence.__file__).with_name("assets")
    assert (asset_dir / "MiniPresence.ico").is_file()
    assert (asset_dir / "MiniPresence.png").is_file()
    assert (asset_dir / "MP-text-icon.png").is_file()
