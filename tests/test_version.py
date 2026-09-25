import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from version import __version__


def test_release_version_metadata_is_synchronized():
    root_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    mobile_version = json.loads((ROOT / "mobile" / "package.json").read_text(encoding="utf-8"))["version"]
    assert root_version == __version__
    assert root_version == mobile_version


def test_v040_release_version():
    assert __version__ == "0.4.0"
