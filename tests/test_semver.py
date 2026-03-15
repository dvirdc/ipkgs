"""Tests for semver helpers."""

from __future__ import annotations

import pytest

from ipkgs.utils.semver import satisfies, latest_matching, bump


@pytest.mark.parametrize("version,constraint,expected", [
    # Caret
    ("1.2.3", "^1.0.0", True),
    ("1.9.9", "^1.0.0", True),
    ("2.0.0", "^1.0.0", False),
    ("0.9.9", "^1.0.0", False),
    # Tilde
    ("1.2.5", "~1.2.0", True),
    ("1.3.0", "~1.2.0", False),
    # Exact
    ("1.2.3", "1.2.3", True),
    ("1.2.4", "1.2.3", False),
    ("1.2.3", "=1.2.3", True),
    # Comparison
    ("1.5.0", ">=1.0.0", True),
    ("0.9.0", ">=1.0.0", False),
    ("1.0.0", "<=1.0.0", True),
    ("1.0.1", "<=1.0.0", False),
    ("1.1.0", ">1.0.0", True),
    ("1.0.0", ">1.0.0", False),
    ("0.9.0", "<1.0.0", True),
    # Wildcard
    ("999.0.0", "*", True),
    # Range
    ("1.5.0", ">=1.0.0 <2.0.0", True),
    ("2.0.0", ">=1.0.0 <2.0.0", False),
])
def test_satisfies(version: str, constraint: str, expected: bool) -> None:
    assert satisfies(version, constraint) == expected


def test_latest_matching() -> None:
    versions = ["1.0.0", "1.2.0", "1.9.0", "2.0.0"]
    assert latest_matching(versions, "^1.0.0") == "1.9.0"
    assert latest_matching(versions, "^2.0.0") == "2.0.0"
    assert latest_matching(versions, "^3.0.0") is None


def test_bump() -> None:
    assert bump("1.2.3", "patch") == "1.2.4"
    assert bump("1.2.3", "minor") == "1.3.0"
    assert bump("1.2.3", "major") == "2.0.0"
