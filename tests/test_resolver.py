"""Tests for DependencyResolver."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ipkgs.core.manifest import IpkgsManifest
from ipkgs.core.package import PackageMetadata, PackageVersion
from ipkgs.core.resolver import DependencyResolver
from ipkgs.exceptions import DependencyConflictError, PackageNotFoundError


def _make_pkg(name: str, versions: dict[str, dict]) -> PackageMetadata:
    """Helper to build a PackageMetadata with given {version: {deps}} map."""
    pkg_versions = {}
    for v, deps in versions.items():
        pkg_versions[v] = PackageVersion(
            version=v,
            tarball_url=f"https://api.ipkgs.com/v1/packages/{name}/-/{name}-{v}.tar.gz",
            integrity=f"sha256-{name}-{v}",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            dependencies=deps,
        )
    latest = sorted(pkg_versions)[-1]
    return PackageMetadata(
        name=name,
        latest=latest,
        versions=pkg_versions,
    )


def _make_registry(*pkgs: PackageMetadata) -> dict[str, PackageMetadata]:
    return {p.name: p for p in pkgs}


def test_simple_single_dep() -> None:
    registry = _make_registry(
        _make_pkg("fifo-sync", {"2.0.0": {}, "2.1.0": {}}),
    )
    manifest = IpkgsManifest(name="my-core", version="1.0.0", dependencies={"fifo-sync": "^2.0.0"})
    resolver = DependencyResolver(fetch_fn=lambda n: registry[n])
    resolved = resolver.resolve(manifest)
    assert resolved["fifo-sync"] == "2.1.0"


def test_transitive_dependency() -> None:
    registry = _make_registry(
        _make_pkg("pkg-b", {"1.0.0": {"pkg-c": "^1.0.0"}}),
        _make_pkg("pkg-c", {"1.0.0": {}, "1.2.0": {}}),
    )
    manifest = IpkgsManifest(name="pkg-a", version="1.0.0", dependencies={"pkg-b": "^1.0.0"})
    resolver = DependencyResolver(fetch_fn=lambda n: registry[n])
    resolved = resolver.resolve(manifest)
    assert "pkg-b" in resolved
    assert "pkg-c" in resolved
    assert resolved["pkg-c"] == "1.2.0"


def test_diamond_dependency() -> None:
    # A -> B@^1, A -> C@^1, B -> D@^1, C -> D@^1
    registry = _make_registry(
        _make_pkg("pkg-b", {"1.0.0": {"pkg-d": "^1.0.0"}}),
        _make_pkg("pkg-c", {"1.0.0": {"pkg-d": "^1.0.0"}}),
        _make_pkg("pkg-d", {"1.0.0": {}, "1.5.0": {}}),
    )
    manifest = IpkgsManifest(
        name="pkg-a",
        version="1.0.0",
        dependencies={"pkg-b": "^1.0.0", "pkg-c": "^1.0.0"},
    )
    resolver = DependencyResolver(fetch_fn=lambda n: registry[n])
    resolved = resolver.resolve(manifest)
    # Both B and C need D@^1 — should resolve to single version
    assert resolved["pkg-d"] == "1.5.0"


def test_conflict_raises() -> None:
    # A requires D@^1, B requires D@^2 — incompatible
    registry = _make_registry(
        _make_pkg("pkg-b", {"1.0.0": {"pkg-d": "^2.0.0"}}),
        _make_pkg("pkg-d", {"1.0.0": {}, "2.0.0": {}}),
    )
    manifest = IpkgsManifest(
        name="pkg-a",
        version="1.0.0",
        dependencies={"pkg-b": "^1.0.0", "pkg-d": "^1.0.0"},
    )
    resolver = DependencyResolver(fetch_fn=lambda n: registry[n])
    with pytest.raises(DependencyConflictError):
        resolver.resolve(manifest)


def test_package_not_found_raises() -> None:
    manifest = IpkgsManifest(name="my-core", version="1.0.0", dependencies={"missing-pkg": "^1.0.0"})

    def fetch(name: str) -> PackageMetadata:
        raise PackageNotFoundError(name)

    resolver = DependencyResolver(fetch_fn=fetch)
    with pytest.raises(PackageNotFoundError):
        resolver.resolve(manifest)
