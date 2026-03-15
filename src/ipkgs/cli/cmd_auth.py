"""ipkgs login / logout — registry authentication."""

from __future__ import annotations

import asyncio

import click

from ipkgs.cli.main import IpkgsContext
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.auth import AuthManager
from ipkgs.utils.console import print_success, print_error


@click.command("login")
@click.option("--username", "-u", prompt=True)
@click.option("--password", "-p", prompt=True, hide_input=True)
@click.pass_obj
def login(ctx: IpkgsContext, username: str, password: str) -> None:
    """Authenticate with the ipkgs.com registry."""
    try:
        auth = AuthManager(ctx.registry)
        token = asyncio.run(auth.login(username, password))
        print_success(ctx.console, f"Logged in as [bold]{username}[/]")
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)


@click.command("logout")
@click.pass_obj
def logout(ctx: IpkgsContext) -> None:
    """Remove stored credentials for the registry."""
    auth = AuthManager(ctx.registry)
    auth.clear_token()
    print_success(ctx.console, "Logged out.")
