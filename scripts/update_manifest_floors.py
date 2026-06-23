"""Raise the `>=` dependency floors in manifest.json to the latest PyPI release.

Dependabot cannot read manifest.json, and the requirements use open `>=`
ranges, so this keeps the minimum versions current for safety and feature
compatibility. Only simple single `>=` specifiers are touched; anything more
complex is left for a human. Run with --check to report without writing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.request import urlopen

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

MANIFEST = Path("custom_components/ocado/manifest.json")


def latest_release(package: str) -> Version | None:
    """Return the latest non-prerelease, non-yanked version on PyPI."""
    with urlopen(f"https://pypi.org/pypi/{package}/json", timeout=30) as resp:
        data = json.load(resp)
    candidates: list[Version] = []
    for raw, files in data["releases"].items():
        if not files or all(f.get("yanked") for f in files):
            continue
        try:
            version = Version(raw)
        except InvalidVersion:
            continue
        if not version.is_prerelease:
            candidates.append(version)
    return max(candidates) if candidates else None


def new_floor(requirement: str) -> str | None:
    """Return an updated requirement string if its `>=` floor can be raised."""
    req = Requirement(requirement)
    specs = list(req.specifier)
    if len(specs) != 1 or specs[0].operator != ">=":
        return None
    current = Version(specs[0].version)
    latest = latest_release(req.name)
    if latest is None or latest <= current:
        return None
    return requirement.replace(f">={specs[0].version}", f">={latest}")


def main() -> int:
    """Update manifest floors, returning 0 and printing whether anything changed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report without writing")
    args = parser.parse_args()

    text = MANIFEST.read_text()
    manifest = json.loads(text)
    changes: list[tuple[str, str]] = []
    for requirement in manifest.get("requirements", []):
        updated = new_floor(requirement)
        if updated and updated != requirement:
            changes.append((requirement, updated))

    for old, new in changes:
        print(f"{old} -> {new}")
        text = text.replace(old, new)

    if changes and not args.check:
        MANIFEST.write_text(text)

    print(f"changed={'true' if changes else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
