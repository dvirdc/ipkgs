"""ipkgs — Verilog IP core package manager."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ipkgs")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
