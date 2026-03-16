"""ipkgs login / logout — registry authentication."""

from __future__ import annotations

import click

from ipkgs.cli.main import IpkgsContext
from ipkgs.registry.auth import AuthManager
from ipkgs.utils.console import print_success, print_error


@click.command("login")
@click.option("--token", "-t", prompt="API token", hide_input=True,
              help="API token from ipkgs.com/settings/tokens")
@click.pass_obj
def login(ctx: IpkgsContext, token: str) -> None:
    """Save an API token for the ipkgs.com registry.

    Generate a token at: https://ipkgs.com/settings/tokens

    \b
    Examples:
      ipkgs login --token <your-token>
      IPKGS_TOKEN=<your-token> ipkgs publish   # alternative: env var
    """
    token = token.strip()
    if not token:
        print_error(ctx.console, "Token cannot be empty.")
        raise SystemExit(1)
    auth = AuthManager(ctx.registry)
    auth.set_token(token)
    print_success(ctx.console, "Token saved. You can now run [cyan]ipkgs publish[/].")


@click.command("logout")
@click.pass_obj
def logout(ctx: IpkgsContext) -> None:
    """Remove stored credentials for the registry."""
    auth = AuthManager(ctx.registry)
    auth.clear_token()
    print_success(ctx.console, "Logged out.")
