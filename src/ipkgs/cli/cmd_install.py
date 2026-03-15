"""ipkgs install — install IP core packages."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.installer import Installer
from ipkgs.core.lockfile import IpkgsLock, LOCKFILE_FILENAME
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.core.resolver import DependencyResolver
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import make_progress, print_success, print_error, print_warning
from ipkgs.utils.fs import find_project_root, ensure_ip_modules_dir


@click.command("install")
@click.argument("packages", nargs=-1)
@click.option("--save-dev", is_flag=True, help="Add to devDependencies.")
@click.option("--no-lockfile", is_flag=True, help="Skip writing ipkgs.lock.")
@click.option("--dry-run", is_flag=True, help="Show what would be installed without doing it.")
@click.pass_obj
def install(
    ctx: IpkgsContext,
    packages: tuple[str, ...],
    save_dev: bool,
    no_lockfile: bool,
    dry_run: bool,
) -> None:
    """Install Verilog IP core packages.

    With no arguments, installs all dependencies from ipkgs.json.
    Pass package names to install and add to ipkgs.json.

    \b
    Examples:
      ipkgs install
      ipkgs install uart-core
      ipkgs install uart-core@^1.2.0 fifo-sync@^2.0.0
    """
    try:
        asyncio.run(_install(ctx, packages, save_dev, no_lockfile, dry_run))
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


async def _install(
    ctx: IpkgsContext,
    packages: tuple[str, ...],
    save_dev: bool,
    no_lockfile: bool,
    dry_run: bool,
) -> None:
    root = find_project_root()
    manifest = IpkgsManifest.load(root / MANIFEST_FILENAME)
    lock = IpkgsLock.load(root / LOCKFILE_FILENAME)
    client = RegistryClient(base_url=ctx.registry)

    # Parse package@version args
    if packages:
        for pkg in packages:
            name, _, version_constraint = pkg.partition("@")
            constraint = version_constraint or "latest"
            if constraint == "latest":
                # Fetch latest from registry
                metadata = await client.get_package(name)
                constraint = f"^{metadata.latest}"
            if save_dev:
                manifest.dev_dependencies[name] = constraint
            else:
                manifest.dependencies[name] = constraint

    # Resolve dependency tree
    async def fetch(name: str):  # type: ignore[return]
        return await client.get_package(name)

    def fetch_sync(name: str):  # type: ignore[return]
        return asyncio.get_event_loop().run_until_complete(fetch(name))

    resolver = DependencyResolver(fetch_fn=lambda n: asyncio.get_event_loop().run_until_complete(client.get_package(n)))

    # Use a fresh event loop for synchronous resolution within async context
    resolved = await asyncio.get_event_loop().run_in_executor(None, resolver.resolve, manifest)

    if dry_run:
        ctx.console.print("[bold]Would install:[/]")
        for name, version in sorted(resolved.items()):
            ctx.console.print(f"  [cyan]{name}[/]@{version}")
        return

    ip_modules = ensure_ip_modules_dir(root)
    installer = Installer(ip_modules, client, ctx.console)

    # Find what actually needs installing
    to_install = {
        name: ver
        for name, ver in resolved.items()
        if not installer.is_installed(name, ver)
    }

    if not to_install:
        print_success(ctx.console, "All packages already up to date.")
        return

    ctx.console.print(f"Installing [bold]{len(to_install)}[/] package(s)...")

    with make_progress(ctx.console) as progress:
        for name, version in to_install.items():
            pkg_meta = await client.get_package(name)
            pkg_ver = pkg_meta.get_version(version)
            if pkg_ver is None:
                print_warning(ctx.console, f"Version {version} of {name!r} not found in registry.")
                continue
            await installer.install_package(
                name=name,
                version=version,
                tarball_url=pkg_ver.tarball_url,
                integrity=pkg_ver.integrity,
                progress=progress,
            )
            # Update lock
            from ipkgs.core.lockfile import LockedPackage
            lock.packages[name] = LockedPackage(
                version=version,
                resolved=pkg_ver.tarball_url,
                integrity=pkg_ver.integrity,
                dependencies=pkg_ver.dependencies,
            )

    # Save updated manifest and lock
    if packages:
        manifest.save(root / MANIFEST_FILENAME)

    if not no_lockfile:
        lock.save(root / LOCKFILE_FILENAME)

    print_success(ctx.console, f"Installed {len(to_install)} package(s).")
