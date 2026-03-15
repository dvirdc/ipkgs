"""Installer — download, verify, and extract IP core packages."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from ipkgs.exceptions import IntegrityError, InstallError

IP_MODULES_DIR = "ip_modules"


class Installer:
    def __init__(
        self,
        ip_modules_dir: Path,
        registry_client: "RegistryClient",  # type: ignore[name-defined]  # avoid circular
        console: Console,
    ) -> None:
        self._modules = ip_modules_dir
        self._client = registry_client
        self._console = console

    async def install_package(
        self,
        name: str,
        version: str,
        tarball_url: str,
        integrity: str,
        progress: Progress,
    ) -> None:
        """Download, verify, and extract a single package atomically."""
        self._modules.mkdir(parents=True, exist_ok=True)
        dest = self._modules / name

        task = progress.add_task(f"  [cyan]{name}@{version}[/]", total=None)

        # Download to a temp dir so a failed install leaves no partial state
        tmp_dir = self._modules / f".tmp_{name}"
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tarball_path = tmp_dir / f"{name}-{version}.tar.gz"

            def on_chunk(n: int) -> None:
                progress.advance(task, n)

            await self._client.download_tarball(tarball_url, tarball_path, on_chunk)

            self._verify_integrity(tarball_path, integrity)

            # Extract into tmp_dir/pkg/
            extract_dir = tmp_dir / "pkg"
            extract_dir.mkdir()
            with tarfile.open(tarball_path, "r:gz") as tf:
                tf.extractall(extract_dir)

            # Move into place (remove existing version first)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(extract_dir), str(dest))

            progress.update(task, completed=True, description=f"  [green]✓[/] {name}@{version}")
        except Exception as exc:
            progress.update(task, description=f"  [red]✗[/] {name}@{version}")
            if not isinstance(exc, (IntegrityError, InstallError)):
                raise InstallError(f"Failed to install {name}@{version}: {exc}") from exc
            raise
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def uninstall_package(self, name: str) -> None:
        """Remove ip_modules/<name>/ atomically via rename-then-delete."""
        dest = self._modules / name
        if not dest.exists():
            return
        # Rename first so the directory disappears instantly from the tree
        tombstone = self._modules / f".del_{name}"
        dest.rename(tombstone)
        shutil.rmtree(tombstone)

    def is_installed(self, name: str, version: str) -> bool:
        manifest_path = self._modules / name / "ipkgs.json"
        if not manifest_path.exists():
            return False
        try:
            data = json.loads(manifest_path.read_text())
            return data.get("version") == version
        except Exception:
            return False

    def _verify_integrity(self, path: Path, expected: str) -> None:
        """Raise IntegrityError if sha256 digest doesn't match."""
        if not expected.startswith("sha256-"):
            raise IntegrityError(f"Unsupported integrity format: {expected!r}")
        expected_hex = expected[len("sha256-"):]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != expected_hex:
            raise IntegrityError(
                f"Integrity check failed for {path.name}: "
                f"expected {expected_hex}, got {sha}"
            )
