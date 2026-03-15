"""ipkgs.json manifest model."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from ipkgs.exceptions import ManifestNotFoundError, ManifestValidationError

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
_SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(-[0-9A-Za-z\-\.]+)?(\+[0-9A-Za-z\-\.]+)?$"
)

MANIFEST_FILENAME = "ipkgs.json"


class IpkgsManifest(BaseModel):
    """Schema for ipkgs.json."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    repository: str = ""
    homepage: str = ""

    # Verilog-specific fields
    top_module: str = ""
    platforms: list[str] = []
    source_files: list[str] = []
    include_dirs: list[str] = []
    parameters: dict[str, str] = {}

    # Dependency maps: {"package-name": "^1.2.0"}
    dependencies: dict[str, str] = {}
    dev_dependencies: dict[str, str] = {}

    # Lifecycle scripts: {"sim": "iverilog ..."}
    scripts: dict[str, str] = {}

    # Publish include list (empty = all non-excluded files)
    files: list[str] = []

    # Prevent accidental publish
    private: bool = False

    # Manifest schema version
    ipkgs_version: str = "1"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(
                f"Invalid package name {v!r}. "
                "Must be lowercase alphanumeric with hyphens, e.g. 'uart-core'."
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(
                f"Invalid version {v!r}. Must be semver, e.g. '1.2.0'."
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def check_not_private_publish(cls, data: Any) -> Any:
        return data

    @classmethod
    def load(cls, path: Path | None = None) -> "IpkgsManifest":
        """Load manifest from path or search upward from cwd."""
        if path is None:
            from ipkgs.utils.fs import find_project_root
            root = find_project_root()
            path = root / MANIFEST_FILENAME
        if not path.exists():
            raise ManifestNotFoundError(f"No {MANIFEST_FILENAME} found at {path}")
        try:
            data = json.loads(path.read_text())
            return cls.model_validate(data)
        except (json.JSONDecodeError, Exception) as exc:
            raise ManifestValidationError(str(exc)) from exc

    def save(self, path: Path) -> None:
        """Write manifest to path as formatted JSON."""
        path.write_text(
            json.dumps(self.model_dump(exclude_none=False), indent=2) + "\n"
        )
