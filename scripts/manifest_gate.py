"""Decide whether a PR's manifest version is a valid bump for its label."""
from __future__ import annotations

import argparse
import re
import sys

Version = tuple[int, int, int]
_PRERELEASE = re.compile(r"(rc|alpha|beta|a|b|dev)[0-9]*$", re.IGNORECASE)


def is_prerelease(version: str) -> bool:
    """Return True when the version carries a prerelease suffix."""
    return _PRERELEASE.search(version) is not None


def parse_semver(version: str) -> Version:
    """Parse the leading X.Y.Z, tolerating a prerelease suffix."""
    match = re.match(r"^([0-9]+)\.([0-9]+)\.([0-9]+)", version)  # de-anchored: tolerate rcN
    if not match:
        raise ValueError(f"cannot parse version: {version!r}")
    return int(match[1]), int(match[2]), int(match[3])


def label_bump(labels: list[str]) -> str | None:
    """Map PR labels to the bump tier they justify, or None."""
    joined = " ".join(labels).lower()
    if re.search(r"xfeat|xfeature|major", joined):
        return "major"
    if re.search(r"feat|feature|minor", joined):
        return "minor"
    if re.search(r"fix|patch|chore|bugfix|bug", joined):
        return "patch"
    return None


def _bump(base: Version, tier: str) -> Version:
    major, minor, patch = base
    if tier == "major":
        return (major + 1, 0, 0)
    if tier == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _fmt(version: Version) -> str:
    return "v{}.{}.{}".format(*version)


def evaluate(last_release: str, main_version: str, pr_version: str,
             labels: list[str], *, dependabot: bool = False) -> tuple[bool, str]:
    """Return (ok, reason) for the PR version given the last release and labels."""
    if dependabot:
        return True, "dependabot exempt"
    base = parse_semver(last_release or "0.0.0")
    if is_prerelease(pr_version):
        if pr_version == last_release:
            return False, f"prerelease v{pr_version} must differ from last release"
        return True, "prerelease differs from last release"
    pr = parse_semver(pr_version)
    if pr == base:
        # Graduating an rc line to its same-number final (2.0.0rc19 -> 2.0.0): the
        # de-anchored parse makes both (x,y,z), but AwesomeVersion knows final > its
        # own prerelease, so allow it instead of demanding a label-derived bump.
        if is_prerelease(last_release):
            return True, f"final v{pr_version} graduates prerelease {last_release}"
        return False, f"manifest v{pr_version} == last release; bump it"
    tier = label_bump(labels)
    if tier is None:
        return True, "no managed label; version only needs to differ from last release"
    floor = _bump(base, tier)
    if pr < floor:
        return False, f"{tier} needs >= {_fmt(floor)}, got v{pr_version} (under-bumped)"
    main = parse_semver(main_version) if main_version else floor
    ceiling = max(floor, main)
    if pr > ceiling:
        return False, f"v{pr_version} exceeds the justified bump (expected <= {_fmt(ceiling)} for {tier})"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args, evaluate the gate, print the verdict and return an exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--last-release", required=True)
    parser.add_argument("--main-version", default="")
    parser.add_argument("--pr-version", required=True)
    parser.add_argument("--labels", default="", help="comma-separated label names")
    parser.add_argument("--dependabot", action="store_true")
    args = parser.parse_args(argv)
    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    ok, reason = evaluate(args.last_release, args.main_version, args.pr_version,
                          labels, dependabot=args.dependabot)
    print(("✅ " if ok else "❌ ") + reason)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
