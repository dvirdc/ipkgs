"""ipkgs init — scaffold a new IP core project."""

from __future__ import annotations

from pathlib import Path

import click
from rich.panel import Panel

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.utils.fs import ensure_ip_modules_dir


@click.command("init")
@click.option("--yes", "-y", is_flag=True, help="Accept all defaults non-interactively.")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing ipkgs.json.")
@click.pass_obj
def init(ctx: IpkgsContext, yes: bool, force: bool) -> None:
    """Scaffold a new Verilog IP core project."""
    cwd = Path.cwd()
    manifest_path = cwd / MANIFEST_FILENAME

    if manifest_path.exists() and not force:
        ctx.console.print(
            f"[yellow]{MANIFEST_FILENAME} already exists.[/] Use --force to overwrite."
        )
        raise SystemExit(1)

    def ask(prompt: str, default: str, skip: bool = False) -> str:
        if skip:
            return default
        return click.prompt(prompt, default=default)

    name = ask("Package name", cwd.name.lower().replace("_", "-"), yes)
    version = ask("Version", "0.1.0", yes)
    description = ask("Description", "", yes)
    author = ask("Author", "", yes)
    license_ = ask("License", "MIT", yes)
    top_module = ask("Top module name", name.replace("-", "_"), yes)

    if yes:
        platforms = ["generic"]
    else:
        ctx.console.print(
            "Platforms [dim](comma-separated: ice40, ecp5, xc7, generic)[/]"
        )
        raw = click.prompt("Platforms", default="generic")
        platforms = [p.strip() for p in raw.split(",") if p.strip()]

    manifest = IpkgsManifest(
        name=name,
        version=version,
        description=description,
        author=author,
        license=license_,
        top_module=top_module,
        platforms=platforms,
    )
    manifest.save(manifest_path)

    ensure_ip_modules_dir(cwd)

    # Add ip_modules/ to .gitignore if not present
    gitignore = cwd / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if "ip_modules/" not in content:
            gitignore.write_text(content + "\nip_modules/\n")
    else:
        gitignore.write_text("ip_modules/\n")

    ctx.console.print(
        Panel(
            f"[green]Created[/] [bold]{MANIFEST_FILENAME}[/]\n"
            f"[green]Created[/] ip_modules/\n"
            f"[green]Updated[/] .gitignore",
            title=f"[bold cyan]ipkgs init[/] — {name}@{version}",
            expand=False,
        )
    )
