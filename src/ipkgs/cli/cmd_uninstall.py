"""ipkgs uninstall — remove IP core packages."""

from __future__ import annotations

from pathlib import Path

import click

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.installer import Installer
from ipkgs.core.lockfile import IpkgsLock, LOCKFILE_FILENAME
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import print_success, print_error, print_warning
from ipkgs.utils.fs import find_project_root


@click.command("uninstall")
@click.argument("packages", nargs=-1, required=True)
@click.option("--no-save", is_flag=True, help="Remove from disk but keep in ipkgs.json.")
@click.pass_obj
def uninstall(ctx: IpkgsContext, packages: tuple[str, ...], no_save: bool) -> None:
    """Remove installed IP core packages.

    \b
    Examples:
      ipkgs uninstall uart-core
      ipkgs uninstall uart-core fifo-sync
    """
    try:
        root = find_project_root()
        manifest = IpkgsManifest.load(root / MANIFEST_FILENAME)
        lock = IpkgsLock.load(root / LOCKFILE_FILENAME)
        ip_modules = root / "ip_modules"
        client = RegistryClient(base_url=ctx.registry)
        installer = Installer(ip_modules, client, ctx.console)

        removed = []
        for name in packages:
            in_deps = name in manifest.dependencies or name in manifest.dev_dependencies

            if not in_deps and not (ip_modules / name).exists():
                print_warning(ctx.console, f"{name!r} is not installed.")
                continue

            installer.uninstall_package(name)
            removed.append(name)

            if not no_save:
                manifest.dependencies.pop(name, None)
                manifest.dev_dependencies.pop(name, None)

            lock.packages.pop(name, None)

        if not removed:
            return

        if not no_save:
            manifest.save(root / MANIFEST_FILENAME)
        lock.save(root / LOCKFILE_FILENAME)

        print_success(ctx.console, f"Removed: {', '.join(removed)}")

    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)
