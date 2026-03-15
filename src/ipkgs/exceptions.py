"""ipkgs exception hierarchy."""

from __future__ import annotations


class IpkgsError(Exception):
    """Base exception for all ipkgs errors."""


# --- Manifest / config ---

class ManifestNotFoundError(IpkgsError):
    """No ipkgs.json found in the project tree."""


class ManifestValidationError(IpkgsError):
    """ipkgs.json failed schema validation."""


# --- Dependency resolution ---

class DependencyConflictError(IpkgsError):
    """Two packages require incompatible versions of the same dependency."""

    def __init__(self, message: str, conflict_chain: list[str] | None = None) -> None:
        super().__init__(message)
        self.conflict_chain: list[str] = conflict_chain or []


class PackageNotFoundError(IpkgsError):
    """Package does not exist in the registry."""

    def __init__(self, package_name: str) -> None:
        super().__init__(f"Package not found: {package_name!r}")
        self.package_name = package_name


# --- Network / registry ---

class RegistryError(IpkgsError):
    """Generic registry / network error."""


class AuthenticationError(RegistryError):
    """Authentication failed (401/403)."""


class VersionConflictError(RegistryError):
    """Package version already published (409)."""


# --- Install ---

class IntegrityError(IpkgsError):
    """Downloaded tarball failed integrity check."""


class InstallError(IpkgsError):
    """Generic install failure."""
