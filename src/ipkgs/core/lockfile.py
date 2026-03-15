"""ipkgs.lock lockfile model."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ipkgs import __version__

LOCKFILE_FILENAME = "ipkgs.lock"


class LockedPackage(BaseModel):
    version: str
    resolved: str        # full tarball URL
    integrity: str       # "sha256-<hex>"
    dependencies: dict[str, str] = {}


class IpkgsLock(BaseModel):
    lockfile_version: int = 1
    ipkgs_version: str = __version__
    packages: dict[str, LockedPackage] = {}

    @classmethod
    def load(cls, path: Path) -> "IpkgsLock":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls.model_validate(data)

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.model_dump(), indent=2) + "\n"
        )

    def is_satisfied_by(self, manifest_deps: dict[str, str]) -> bool:
        """Return True if all manifest dependencies are already locked."""
        from ipkgs.utils.semver import satisfies
        for name, constraint in manifest_deps.items():
            locked = self.packages.get(name)
            if locked is None:
                return False
            if not satisfies(locked.version, constraint):
                return False
        return True
