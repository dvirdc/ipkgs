"""ipkgs login / logout — registry authentication."""

from __future__ import annotations

import asyncio

import click

from ipkgs.cli.main import IpkgsContext
from ipkgs.exceptions import IpkgsError
from ipkgs.registry.auth import AuthManager
from ipkgs.utils.console import print_success, print_error


@click.command("login")
@click.option(
    "--provider", "-p",
    type=click.Choice(["github", "google"]),
    default="github",
    show_default=True,
    help="OAuth provider to authenticate with.",
)
@click.option(
    "--token", "-t",
    default=None,
    help="Paste a token directly instead of browser login (useful for CI).",
)
@click.pass_obj
def login(ctx: IpkgsContext, provider: str, token: str | None) -> None:
    """Authenticate with the ipkgs.com registry.

    Opens a browser window to sign in with GitHub or Google.
    On success the token is stored securely in your OS keyring.

    \b
    Examples:
      ipkgs login                        # GitHub (default)
      ipkgs login --provider google
      ipkgs login --token ipkgs_xxxx     # non-interactive / CI
      IPKGS_TOKEN=ipkgs_xxxx ipkgs publish  # env var alternative
    """
    # Non-interactive path: token passed directly
    if token:
        token = token.strip()
        if not token:
            print_error(ctx.console, "Token cannot be empty.")
            raise SystemExit(1)
        auth = AuthManager(ctx.registry)
        auth.set_token(token)
        print_success(ctx.console, "Token saved. You can now run [cyan]ipkgs publish[/].")
        return

    # Browser OAuth flow
    ctx.console.print(
        f"Opening browser to sign in with [bold]{provider.capitalize()}[/]...\n"
        f"[dim]Waiting for callback on http://localhost:9876/callback[/]"
    )
    try:
        api_token = asyncio.run(_do_login(ctx.registry, provider))
        print_success(
            ctx.console,
            f"Logged in via {provider.capitalize()}. Token stored in keyring.",
        )
        if ctx.verbose:
            ctx.console.print(f"[dim]Token: {api_token[:12]}...[/]")
    except TimeoutError:
        print_error(ctx.console, "Timed out waiting for browser authentication.")
        raise SystemExit(1)
    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)
    except Exception as exc:
        print_error(ctx.console, f"Login failed: {exc}")
        raise SystemExit(1)


async def _do_login(registry: str, provider: str) -> str:
    auth = AuthManager(registry)
    return await auth.login_browser(provider=provider)


@click.command("logout")
@click.pass_obj
def logout(ctx: IpkgsContext) -> None:
    """Remove stored credentials for the registry."""
    auth = AuthManager(ctx.registry)
    auth.clear_token()
    print_success(ctx.console, "Logged out.")
