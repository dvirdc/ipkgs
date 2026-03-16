"""ipkgs update — update IP core packages to newer versions."""

from __future__ import annotations

import asyncio

import click
from rich.table import Table

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.lockfile import IpkgsLock, LockedPackage, LOCKFILE_FILENAME
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import make_progress, print_success, print_error
from ipkgs.utils.fs import find_project_root, ensure_ip_modules_dir
from ipkgs.utils.semver import latest_matching
from ipkgs.core.installer import Installer


@click.command("update")
@click.argument("packages", nargs=-1)
@click.option("--latest", "use_latest", is_flag=True, help="Ignore semver range, update to absolute latest.")
@click.pass_obj
def update(ctx: IpkgsContext, packages: tuple[str, ...], use_latest: bool) -> None:
    """Update installed IP core packages.

    With no arguments, updates all direct dependencies within their semver ranges.
    Pass package names to update specific packages.

    \b
    Examples:
      ipkgs update
      ipkgs update uart-core
      ipkgs update --latest uart-core
    """
    try:
        asyncio.run(_update(ctx, packages, use_latest))
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


async def _update(ctx: IpkgsContext, packages: tuple[str, ...], use_latest: bool) -> None:
    root = find_project_root()
    manifest = IpkgsManifest.load(root / MANIFEST_FILENAME)
    lock = IpkgsLock.load(root / LOCKFILE_FILENAME)
    client = RegistryClient(base_url=ctx.registry)
    ip_modules = ensure_ip_modules_dir(root)
    installer = Installer(ip_modules, client, ctx.console)

    # Determine which packages to check
    targets = list(packages) if packages else list(manifest.dependencies.keys())

    if use_latest and not packages:
        if not click.confirm("Update ALL packages to absolute latest (ignores semver range)?"):
            return

    updates: list[tuple[str, str, str, str, str]] = []  # (name, old_ver, new_ver, tarball, integrity)

    for name in targets:
        constraint = manifest.dependencies.get(name) or manifest.dev_dependencies.get(name)
        if constraint is None:
            ctx.console.print(f"[yellow]{name!r} is not in ipkgs.json dependencies — skipping.[/]")
            continue

        meta = await client.get_package(name)
        available = list(meta.versions.keys())

        if use_latest:
            new_version = meta.latest
        else:
            new_version = latest_matching(available, constraint)

        if new_version is None:
            ctx.console.print(f"[yellow]No update available for {name!r}.[/]")
            continue

        old_locked = lock.packages.get(name)
        old_version = old_locked.version if old_locked else "not installed"

        if new_version == old_version:
            continue

        pkg_ver = meta.versions[new_version]
        updates.append((name, old_version, new_version, pkg_ver.integrity))

    if not updates:
        print_success(ctx.console, "All packages are up to date.")
        return

    table = Table(title="Updates available")
    table.add_column("Package", style="cyan")
    table.add_column("From", style="yellow")
    table.add_column("To", style="green")
    for name, old, new, _ in updates:
        table.add_row(name, old, new)
    ctx.console.print(table)

    with make_progress(ctx.console) as progress:
        for name, old_version, new_version, integrity in updates:
            await installer.install_package(
                name=name,
                version=new_version,
                integrity=integrity,
                progress=progress,
            )
            lock.packages[name] = LockedPackage(
                version=new_version,
                resolved=f"{ctx.registry}/packages/{name}/{new_version}/download",
                integrity=integrity,
            )

    lock.save(root / LOCKFILE_FILENAME)
    print_success(ctx.console, f"Updated {len(updates)} package(s).")
