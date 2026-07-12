"""Tests for the entity-translations quality-scale rule.

Every ``_attr_translation_key`` an entity class declares must resolve to a name
in ``strings.json`` (hassfest does not check this), and ``translations/en.json``
must stay a copy of ``strings.json``. ``_attr_*`` are descriptors on HA's base
class, so the literal a subclass sets is read from ``cls.__dict__``.
"""

import json
from pathlib import Path
import re

from custom_components.ocado import sensor as ocado_sensor

PACKAGE = Path(ocado_sensor.__file__).parent
STRINGS = json.loads((PACKAGE / "strings.json").read_text())
_KEY_RE = re.compile(r"""_attr_translation_key\s*=\s*["'](\w+)["']""")


def _translation_keys(filename: str) -> list[str]:
    """Return every translation-key literal assigned in the platform source."""
    return _KEY_RE.findall((PACKAGE / filename).read_text())


def test_entity_translation_keys_resolve() -> None:
    """Each translation key used in code has a name in strings.json."""
    entity = STRINGS["entity"]
    checks = [("sensor", _translation_keys("sensor.py")), ("calendar", _translation_keys("calendar.py"))]
    assert "missing_items" in checks[0][1]
    assert "substituted_items" in checks[0][1]
    for platform, keys in checks:
        for key in keys:
            assert key in entity[platform], f"{platform}.{key} missing from strings.json"
            assert entity[platform][key].get("name"), f"{platform}.{key} has no name"


def test_en_json_matches_strings() -> None:
    """translations/en.json stays a copy of strings.json's entity section."""
    en = json.loads((PACKAGE / "translations" / "en.json").read_text())
    assert en["entity"] == STRINGS["entity"]
