"""ipkgs list — list installed IP core packages."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.tree import Tree

from ipkgs.cli.main import IpkgsContext
from ipkgs.core.manifest import IpkgsManifest, MANIFEST_FILENAME
from ipkgs.exceptions import IpkgsError
from ipkgs.utils.console import print_error
from ipkgs.utils.fs import find_project_root


@click.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
@click.option("--depth", default=0, help="Tree depth (0 = unlimited).")
@click.pass_obj
def list_packages(ctx: IpkgsContext, as_json: bool, depth: int) -> None:
    """List installed Verilog IP core packages.

    \b
    Examples:
      ipkgs list
      ipkgs list --json
    """
    try:
        root = find_project_root()
        manifest = IpkgsManifest.load(root / MANIFEST_FILENAME)
        ip_modules = root / "ip_modules"

        installed: dict[str, dict] = {}
        if ip_modules.exists():
            for entry in sorted(ip_modules.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    pkg_manifest = entry / "ipkgs.json"
                    if pkg_manifest.exists():
                        try:
                            data = json.loads(pkg_manifest.read_text())
                            installed[entry.name] = data
                        except Exception:
                            installed[entry.name] = {"version": "unknown"}

        if as_json:
            import json as _json
            ctx.console.print(_json.dumps(installed, indent=2))
            return

        if not installed:
            ctx.console.print("[dim]No packages installed in ip_modules/[/]")
            return

        tree = Tree(
            f"[bold cyan]{manifest.name}[/]@{manifest.version}",
            guide_style="dim",
        )
        direct = set(manifest.dependencies) | set(manifest.dev_dependencies)

        for name, data in installed.items():
            version = data.get("version", "?")
            is_direct = name in direct
            label = f"[cyan]{name}[/]@{version}"
            if not is_direct:
                label += " [dim](transitive)[/]"
            tree.add(label)

        ctx.console.print(tree)
        ctx.console.print(
            f"\n[dim]{len(installed)} package(s) installed[/]"
        )

    except IpkgsError as exc:
        print_error(ctx.console, str(exc))
        raise SystemExit(1)
