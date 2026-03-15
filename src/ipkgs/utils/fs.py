"""Filesystem helpers."""

from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path

from ipkgs.exceptions import ManifestNotFoundError

MANIFEST_FILENAME = "ipkgs.json"
ALWAYS_EXCLUDE = {".git", "ip_modules", "__pycache__", ".ipkgs_cache", "*.pyc"}


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start until ipkgs.json is found."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        if (directory / MANIFEST_FILENAME).exists():
            return directory
    raise ManifestNotFoundError(
        f"No {MANIFEST_FILENAME} found in {current} or any parent directory. "
        "Run `ipkgs init` to create one."
    )


def ensure_ip_modules_dir(root: Path) -> Path:
    ip_modules = root / "ip_modules"
    ip_modules.mkdir(exist_ok=True)
    gitkeep = ip_modules / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    return ip_modules


def build_tarball(root: Path, include_files: list[str] | None = None) -> Path:
    """
    Create a .tar.gz of the project in a temp directory.
    Returns the path to the tarball.
    """
    tmp = Path(tempfile.mkdtemp())
    tarball = tmp / f"package.tar.gz"

    def _should_include(path: Path) -> bool:
        for part in path.parts:
            if part.startswith(".git"):
                return False
            if part == "ip_modules":
                return False
            if part == "__pycache__":
                return False
            if part.endswith(".pyc"):
                return False
        if include_files:
            rel = path.relative_to(root)
            return any(str(rel).startswith(f) for f in include_files)
        return True

    with tarfile.open(tarball, "w:gz") as tf:
        for item in sorted(root.rglob("*")):
            if item.is_file() and _should_include(item):
                tf.add(item, arcname=item.relative_to(root))

    return tarball


def atomic_rmtree(path: Path) -> None:
    """Rename to a tombstone name then delete, for safer directory removal."""
    tombstone = path.parent / f".del_{path.name}"
    path.rename(tombstone)
    shutil.rmtree(tombstone)
