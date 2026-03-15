"""Tests for IpkgsLock."""

from __future__ import annotations

from pathlib import Path

from ipkgs.core.lockfile import IpkgsLock, LockedPackage
from ipkgs.core.manifest import IpkgsManifest


def test_round_trip(tmp_path: Path) -> None:
    lock = IpkgsLock(
        packages={
            "fifo-sync": LockedPackage(
                version="2.1.0",
                resolved="https://api.ipkgs.com/v1/packages/fifo-sync/-/fifo-sync-2.1.0.tar.gz",
                integrity="sha256-abc",
            )
        }
    )
    path = tmp_path / "ipkgs.lock"
    lock.save(path)
    loaded = IpkgsLock.load(path)
    assert loaded.packages["fifo-sync"].version == "2.1.0"


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    lock = IpkgsLock.load(tmp_path / "ipkgs.lock")
    assert lock.packages == {}


def test_is_satisfied_by_true(sample_manifest: IpkgsManifest) -> None:
    lock = IpkgsLock(
        packages={
            "fifo-sync": LockedPackage(
                version="2.1.0",
                resolved="https://example.com/fifo-sync-2.1.0.tar.gz",
                integrity="sha256-abc",
            )
        }
    )
    assert lock.is_satisfied_by(sample_manifest.dependencies)


def test_is_satisfied_by_false_missing(sample_manifest: IpkgsManifest) -> None:
    lock = IpkgsLock()
    assert not lock.is_satisfied_by(sample_manifest.dependencies)


def test_is_satisfied_by_false_wrong_version(sample_manifest: IpkgsManifest) -> None:
    # fifo-sync@1.0.0 doesn't satisfy ^2.0.0
    lock = IpkgsLock(
        packages={
            "fifo-sync": LockedPackage(
                version="1.0.0",
                resolved="https://example.com/fifo-sync-1.0.0.tar.gz",
                integrity="sha256-abc",
            )
        }
    )
    assert not lock.is_satisfied_by(sample_manifest.dependencies)
