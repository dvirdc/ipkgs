"""ipkgs publish — publish an IP core to the registry."""

from __future__ import annotations

import asyncio
import hashlib

import click
from rich.panel import Panel

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.auth import AuthManager
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import print_success, print_error
from ipkgs.utils.fs import find_project_root, build_tarball


@click.command("publish")
@click.option("--tag", default="latest", show_default=True, help="Dist-tag for this release.")
@click.option("--dry-run", is_flag=True, help="Build tarball but do not upload.")
@click.pass_obj
def publish(ctx: IpkgsContext, tag: str, dry_run: bool) -> None:
    """Publish this IP core package to the registry.

    \b
    Requires authentication — run `ipkgs login` first,
    or set the IPKGS_TOKEN environment variable.
    """
    try:
        asyncio.run(_publish(ctx, tag, dry_run))
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


async def _publish(ctx: IpkgsContext, tag: str, dry_run: bool) -> None:
    root = find_project_root()
    manifest = IpkgsManifest.load(root / MANIFEST_FILENAME)

    if manifest.private:
        print_error(ctx.console, 'This package is marked "private" — publish aborted.')
        raise SystemExit(1)

    auth = AuthManager(ctx.registry)
    token = auth.get_token()
    if not token and not dry_run:
        print_error(ctx.console, "Not authenticated. Run `ipkgs login` or set IPKGS_TOKEN.")
        raise SystemExit(1)

    ctx.console.print(
        f"Building tarball for [bold cyan]{manifest.name}[/]@{manifest.version}..."
    )
    tarball = build_tarball(root, manifest.files or None)
    integrity = "sha256-" + hashlib.sha256(tarball.read_bytes()).hexdigest()
    size_kb = tarball.stat().st_size / 1024

    ctx.console.print(
        Panel(
            f"[bold]{manifest.name}[/]@{manifest.version}\n"
            f"Size: {size_kb:.1f} KB\n"
            f"Integrity: {integrity}\n"
            f"Tag: {tag}",
            title="Package to publish",
            expand=False,
        )
    )

    if dry_run:
        ctx.console.print("[yellow]Dry run — not uploading.[/]")
        return

    client = RegistryClient(base_url=ctx.registry, token=token)
    url = await client.publish(
        name=manifest.name,
        version=manifest.version,
        tarball=tarball,
        metadata=manifest.model_dump(),
        token=token,  # type: ignore[arg-type]
    )

    print_success(ctx.console, f"Published to {url}")
