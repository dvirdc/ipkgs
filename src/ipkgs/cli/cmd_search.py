"""ipkgs search — search the registry for IP cores."""

from __future__ import annotations

import asyncio

import click
from rich.table import Table

from ipkgs.cli.main import IpkgsContext
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.client import RegistryClient
from ipkgs.utils.console import print_error


@click.command("search")
@click.argument("query")
@click.option("--limit", default=20, show_default=True)
@click.option("--sort", type=click.Choice(["relevance", "downloads", "updated"]), default="relevance")
@click.pass_obj
def search(ctx: IpkgsContext, query: str, limit: int, sort: str) -> None:
    """Search for Verilog IP core packages on ipkgs.com.

    \b
    Examples:
      ipkgs search uart
      ipkgs search fifo --sort downloads
    """
    try:
        asyncio.run(_search(ctx, query, limit, sort))
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


async def _search(ctx: IpkgsContext, query: str, limit: int, sort: str) -> None:
    client = RegistryClient(base_url=ctx.registry)
    results = await client.search(query, limit=limit, sort=sort)

    if not results:
        ctx.console.print(f"[yellow]No packages found for {query!r}.[/]")
        ctx.console.print(
            "Be the first to publish one: [cyan]ipkgs publish[/]"
        )
        return

    table = Table(title=f"Search results for [bold]{query}[/]", show_lines=False)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green", no_wrap=True)
    table.add_column("Description")
    table.add_column("License", no_wrap=True)

    for pkg in results:
        table.add_row(pkg.name, pkg.latest, pkg.description or "-", pkg.license)

    ctx.console.print(table)
    ctx.console.print(
        f"\nInstall with: [cyan]ipkgs install <name>[/]"
    )
