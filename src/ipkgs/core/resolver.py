"""Dependency resolver — pure logic, no I/O."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ipkgs.core.manifest import IpkgsManifest
from ipkgs.core.package import PackageMetadata
from ipkgs.exceptions import DependencyConflictError, PackageNotFoundError
from ipkgs.utils.semver import latest_matching, satisfies


class DependencyResolver:
    """
    Resolve a full, flat dependency graph for a manifest.

    Args:
        fetch_fn: Callable that takes a package name and returns PackageMetadata.
                  Injected so the resolver is testable without network calls.
    """

    def __init__(self, fetch_fn: Callable[[str], PackageMetadata]) -> None:
        self._fetch = fetch_fn
        self._resolved: dict[str, str] = {}
        # Track which packages required each dep (for conflict messages)
        self._required_by: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def resolve(self, manifest: IpkgsManifest) -> dict[str, str]:
        """Return flat {name: exact_version} for the entire dep tree."""
        self._resolved = {}
        self._required_by = defaultdict(list)

        all_deps = {**manifest.dependencies, **manifest.dev_dependencies}
        for name, constraint in all_deps.items():
            self._resolve_recursive(name, constraint, requirer=manifest.name)

        return dict(self._resolved)

    def _resolve_recursive(
        self,
        name: str,
        constraint: str,
        requirer: str,
    ) -> None:
        self._required_by[name].append((requirer, constraint))

        metadata = self._fetch(name)
        available = list(metadata.versions.keys())
        chosen = latest_matching(available, constraint)
        if chosen is None:
            raise PackageNotFoundError(
                f"No version of {name!r} satisfies {constraint!r} "
                f"(available: {', '.join(available) or 'none'})"
            )

        if name in self._resolved:
            existing = self._resolved[name]
            if existing != chosen:
                # Check if both constraints can share one version
                all_constraints = [c for _, c in self._required_by[name]]
                candidates = [
                    v for v in available
                    if all(satisfies(v, c) for c in all_constraints)
                ]
                compatible = latest_matching(candidates, "*") if candidates else None
                if compatible is None:
                    chain = [
                        f"{req} requires {name}@{con}"
                        for req, con in self._required_by[name]
                    ]
                    raise DependencyConflictError(
                        f"Dependency conflict for {name!r}: "
                        + "; ".join(chain),
                        conflict_chain=chain,
                    )
                self._resolved[name] = compatible
            return

        self._resolved[name] = chosen

        # Recurse into transitive dependencies
        pkg_version = metadata.versions[chosen]
        for dep_name, dep_constraint in pkg_version.dependencies.items():
            self._resolve_recursive(dep_name, dep_constraint, requirer=name)
