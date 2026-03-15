"""ipkgs info — show package details."""

from __future__ import annotations

import asyncio

import click
from rich.panel import Panel
from rich.table import Table

from ipkgs.cli.main import IpkgsContext
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import print_error


@click.command("info")
@click.argument("package")
@click.pass_obj
def info(ctx: IpkgsContext, package: str) -> None:
    """Show details about an IP core package.

    \b
    Examples:
      ipkgs info uart-core
      ipkgs info uart-core@1.2.0
    """
    try:
        asyncio.run(_info(ctx, package))
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


async def _info(ctx: IpkgsContext, package: str) -> None:
    name, _, version = package.partition("@")
    client = RegistryClient(base_url=ctx.registry)
    meta = await client.get_package(name)

    target_version = version or meta.latest
    pkg = meta.versions.get(target_version)

    ctx.console.print(
        Panel(
            f"[bold cyan]{meta.name}[/]  [green]{target_version}[/]\n"
            f"{meta.description or '[dim]No description[/]'}",
            expand=False,
        )
    )

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    grid.add_row("Author", meta.author or "-")
    grid.add_row("License", meta.license or "-")
    grid.add_row("Homepage", meta.dict().get("homepage") or "-")
    if pkg:
        grid.add_row("Published", str(pkg.published_at.date()) if pkg.published_at else "-")
        grid.add_row("Downloads", str(pkg.download_count))
    ctx.console.print(grid)

    if pkg and pkg.dependencies:
        dep_table = Table(title="Dependencies", show_header=True, header_style="bold")
        dep_table.add_column("Package", style="cyan")
        dep_table.add_column("Range", style="green")
        for dep_name, constraint in pkg.dependencies.items():
            dep_table.add_row(dep_name, constraint)
        ctx.console.print(dep_table)

    # Versions list
    versions = sorted(meta.versions.keys(), reverse=True)[:10]
    ver_table = Table(title="Recent versions", show_header=True, header_style="bold")
    ver_table.add_column("Version", style="cyan")
    ver_table.add_column("Downloads")
    for v in versions:
        pv = meta.versions[v]
        tag = " [bold green](latest)[/]" if v == meta.latest else ""
        ver_table.add_row(v + tag, str(pv.download_count))
    ctx.console.print(ver_table)

    ctx.console.print(f"\n[dim]Install:[/] [cyan]ipkgs install {meta.name}[/]")
