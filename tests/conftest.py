"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ipkgs.core.manifest import IpkgsManifest
from ipkgs.core.package import PackageMetadata, PackageVersion


@pytest.fixture
def sample_manifest() -> IpkgsManifest:
    return IpkgsManifest(
        name="uart-core",
        version="1.0.0",
        description="A parameterized UART for FPGAs",
        top_module="uart_top",
        platforms=["ice40", "ecp5"],
        dependencies={"fifo-sync": "^2.0.0"},
    )


@pytest.fixture
def sample_package_metadata() -> PackageMetadata:
    return PackageMetadata(
        name="fifo-sync",
        description="Synchronous FIFO",
        author="Test Author",
        license="MIT",
        latest="2.1.0",
        versions={
            "2.0.0": PackageVersion(
                version="2.0.0",
                tarball_url="https://api.ipkgs.com/v1/packages/fifo-sync/-/fifo-sync-2.0.0.tar.gz",
                integrity="sha256-abc123",
                published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                dependencies={},
            ),
            "2.1.0": PackageVersion(
                version="2.1.0",
                tarball_url="https://api.ipkgs.com/v1/packages/fifo-sync/-/fifo-sync-2.1.0.tar.gz",
                integrity="sha256-def456",
                published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
                dependencies={},
            ),
        },
        dist_tags={"latest": "2.1.0"},
    )
