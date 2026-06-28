"""Unit tests for the manifest version gate decision logic."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "manifest_gate", Path(__file__).parents[1] / "scripts" / "manifest_gate.py"
)
assert _SPEC and _SPEC.loader
manifest_gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(manifest_gate)
evaluate = manifest_gate.evaluate


def ok(*args, **kwargs) -> bool:
    """Return just the pass/fail boolean from evaluate."""
    return evaluate(*args, **kwargs)[0]


def test_unchanged_vs_last_release_fails() -> None:
    """A version equal to the last release is rejected."""
    assert not ok("1.1.0", "1.1.0", "1.1.0", ["fix"])


def test_feature_minor_bump_passes() -> None:
    """A feature label with a minor bump passes."""
    assert ok("1.1.0", "1.1.0", "1.2.0", ["feature"])


def test_feature_only_patch_under_bumps() -> None:
    """A feature label that only bumps the patch is rejected."""
    assert not ok("1.1.0", "1.1.0", "1.1.1", ["feature"])


def test_chore_rides_in_cycle_minor() -> None:
    """A chore can sit at an in-cycle minor already on main (shipped regression)."""
    assert ok("1.1.0", "1.2.0", "1.2.0", ["chore"])


def test_chore_overbump_beyond_cycle_fails() -> None:
    """A chore bumping past the in-cycle version is rejected."""
    assert not ok("1.1.0", "1.2.0", "2.0.0", ["chore"])


def test_breaking_major_passes() -> None:
    """A breaking label with a major bump passes."""
    assert ok("1.1.0", "1.2.0", "2.0.0", ["xfeat"])


def test_prerelease_only_needs_to_differ() -> None:
    """A prerelease version only needs to differ from the last release."""
    assert ok("1.1.0", "1.1.0", "2.0.0rc1", ["feature"])
    assert not ok("2.0.0rc1", "2.0.0rc1", "2.0.0rc1", ["feature"])


def test_final_graduates_prerelease() -> None:
    """A final version may graduate its own prerelease line."""
    assert ok("2.0.0rc19", "2.0.0rc20", "2.0.0", ["feature"])
    assert not ok("2.0.0", "2.0.0", "2.0.0", ["feature"])


def test_dependabot_exempt() -> None:
    """Dependabot PRs are exempt from the gate."""
    assert ok("1.1.0", "1.1.0", "1.1.0", [], dependabot=True)


def test_no_managed_label_passes_when_changed() -> None:
    """With no managed label, any changed version passes."""
    assert ok("1.1.0", "1.1.0", "1.1.5", [])
