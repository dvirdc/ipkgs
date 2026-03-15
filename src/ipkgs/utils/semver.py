"""Semver helpers with npm-style range support."""

from __future__ import annotations

import re
from typing import Literal

import semver as _semver


def _parse(v: str) -> _semver.Version:
    return _semver.Version.parse(v)


def satisfies(version: str, constraint: str) -> bool:
    """Return True if version satisfies the npm-style constraint."""
    constraint = constraint.strip()
    v = _parse(version)

    # Exact or prefixed exact: "1.2.3" or "=1.2.3"
    if re.match(r"^=?\d", constraint):
        c = constraint.lstrip("=").strip()
        if re.fullmatch(r"\d+\.\d+\.\d+.*", c):
            return v == _parse(c)

    # Caret: ^1.2.3 — compatible with 1.x.x where x >= given
    if constraint.startswith("^"):
        base = _parse(constraint[1:])
        if base.major != 0:
            return v.major == base.major and v >= base
        if base.minor != 0:
            return v.major == 0 and v.minor == base.minor and v >= base
        return v == base

    # Tilde: ~1.2.3 — patch-level changes only
    if constraint.startswith("~"):
        base = _parse(constraint[1:])
        return v.major == base.major and v.minor == base.minor and v >= base

    # Range: ">=1.0 <2.0"
    if " " in constraint:
        parts = constraint.split()
        return all(satisfies(version, p) for p in parts)

    # Comparison operators
    for op in (">=", "<=", ">", "<", "!="):
        if constraint.startswith(op):
            base = _parse(constraint[len(op):].strip())
            if op == ">=":
                return v >= base
            if op == "<=":
                return v <= base
            if op == ">":
                return v > base
            if op == "<":
                return v < base
            if op == "!=":
                return v != base

    # Wildcard: "*" or "x"
    if constraint in ("*", "x", ""):
        return True

    return False


def latest_matching(versions: list[str], constraint: str) -> str | None:
    """Return the highest version satisfying the constraint."""
    matching = [v for v in versions if satisfies(v, constraint)]
    if not matching:
        return None
    return str(max((_parse(v) for v in matching)))


def bump(version: str, part: Literal["major", "minor", "patch"]) -> str:
    v = _parse(version)
    if part == "major":
        return str(v.bump_major())
    if part == "minor":
        return str(v.bump_minor())
    return str(v.bump_patch())
