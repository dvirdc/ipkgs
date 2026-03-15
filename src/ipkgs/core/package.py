"""Registry package metadata models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PackageVersion(BaseModel):
    version: str
    tarball_url: str
    integrity: str           # "sha256-<hex>"
    published_at: datetime
    download_count: int = 0
    dependencies: dict[str, str] = {}


class PackageMetadata(BaseModel):
    name: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    latest: str              # version string of the "latest" dist-tag
    versions: dict[str, PackageVersion] = {}
    dist_tags: dict[str, str] = {}

    def get_version(self, version: str) -> PackageVersion | None:
        return self.versions.get(version)

    def latest_version(self) -> PackageVersion | None:
        return self.versions.get(self.latest)
