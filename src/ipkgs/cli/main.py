"""ipkgs CLI entry point."""

from __future__ import annotations

import click
from rich.console import Console

from ipkgs import __version__
from ipkgs.exceptions import IpkgsError
from ipkgs.utils.console import make_console, print_error

BANNER = f"[bold cyan]ipkgs[/] [dim]v{__version__}[/] — Verilog IP core package manager"


class IpkgsContext:
    def __init__(self, registry: str, console: Console, verbose: bool) -> None:
        self.registry = registry
        self.console = console
        self.verbose = verbose


@click.group(
    name="ipkgs",
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100},
    invoke_without_command=True,
)
@click.version_option(__version__, "-V", "--version")
@click.option("--registry", default="https://api.ipkgs.com/v1", envvar="IPKGS_REGISTRY", show_default=True)
@click.option("--no-color", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.pass_context
def cli(ctx: click.Context, registry: str, no_color: bool, verbose: bool) -> None:
    """ipkgs — Verilog IP core package manager (ipkgs.com)"""
    console = make_console(no_color=no_color)
    ctx.ensure_object(dict)
    ctx.obj = IpkgsContext(registry=registry, console=console, verbose=verbose)

    if ctx.invoked_subcommand is None:
        console.print(BANNER)
        console.print(ctx.get_help())


def _handle_error(console: Console, exc: Exception, verbose: bool) -> None:
    if isinstance(exc, IpkgsError):
        print_error(console, str(exc))
    else:
        print_error(console, f"Unexpected error: {exc}")
        if verbose:
            import traceback
            console.print_exception()


# Register subcommands
from ipkgs.cli import (  # noqa: E402
    cmd_init,
    cmd_install,
    cmd_uninstall,
    cmd_publish,
    cmd_search,
    cmd_info,
    cmd_list,
    cmd_update,
    cmd_auth,
)

cli.add_command(cmd_init.init)
cli.add_command(cmd_install.install)
cli.add_command(cmd_uninstall.uninstall)
cli.add_command(cmd_publish.publish)
cli.add_command(cmd_search.search)
cli.add_command(cmd_info.info)
cli.add_command(cmd_list.list_packages)
cli.add_command(cmd_update.update)
cli.add_command(cmd_auth.login)
cli.add_command(cmd_auth.logout)
