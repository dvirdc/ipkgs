"""Registry HTTP client."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

import httpx

from ipkgs.core.package import PackageMetadata, PackageVersion
from ipkgs.exceptions import (
    AuthenticationError,
    PackageNotFoundError,
    RegistryError,
    VersionConflictError,
)

DEFAULT_REGISTRY = "https://api.ipkgs.com/api/v1"


class RegistryClient:
    def __init__(self, base_url: str = DEFAULT_REGISTRY, token: str | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers(),
            transport=httpx.AsyncHTTPTransport(retries=3),
            timeout=30.0,
        )

    def _raise_for_status(self, resp: httpx.Response, package_name: str = "") -> None:
        if resp.status_code == 404:
            raise PackageNotFoundError(package_name)
        if resp.status_code in (401, 403):
            raise AuthenticationError("Authentication failed. Run `ipkgs login --token <token>`.")
        if resp.status_code == 409:
            raise VersionConflictError("This version is already published.")
        if resp.status_code >= 400:
            raise RegistryError(f"Registry error {resp.status_code}: {resp.text}")

    async def get_package(self, name: str) -> PackageMetadata:
        async with self._client() as client:
            resp = await client.get(f"/packages/{name}")
            self._raise_for_status(resp, name)
            return PackageMetadata.model_validate(resp.json())

    async def get_version(self, name: str, version: str) -> PackageVersion:
        async with self._client() as client:
            resp = await client.get(f"/packages/{name}/{version}")
            self._raise_for_status(resp, name)
            return PackageVersion.model_validate(resp.json())

    async def search(
        self,
        query: str,
        limit: int = 20,
        sort: str = "relevance",
    ) -> list[PackageMetadata]:
        async with self._client() as client:
            resp = await client.get(
                "/search",
                params={"q": query, "limit": limit, "sort": sort},
            )
            self._raise_for_status(resp)
            data = resp.json()
            return [PackageMetadata.model_validate(p) for p in data.get("packages", data if isinstance(data, list) else [])]

    async def download_tarball(
        self,
        name: str,
        version: str,
        dest: Path,
        on_chunk: Callable[[int], None],
    ) -> None:
        """Stream tarball from /packages/:name/:version/download."""
        async with self._client() as client:
            async with client.stream("GET", f"/packages/{name}/{version}/download") as resp:
                self._raise_for_status(resp, name)
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        on_chunk(len(chunk))

    async def ensure_package_exists(self, name: str, metadata: dict, token: str) -> None:
        """Create the package entry if it doesn't exist yet (POST /packages)."""
        async with httpx.AsyncClient(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0,
        ) as client:
            resp = await client.get(f"/packages/{name}")
            if resp.status_code == 404:
                create_resp = await client.post(
                    "/packages",
                    json={
                        "name": name,
                        "description": metadata.get("description", ""),
                        "repository_url": metadata.get("repository", ""),
                        "homepage": metadata.get("homepage", ""),
                        "license": metadata.get("license", "MIT"),
                        "keywords": metadata.get("platforms", []),
                    },
                )
                self._raise_for_status(create_resp, name)
            elif resp.status_code >= 400:
                self._raise_for_status(resp, name)

    async def publish(
        self,
        name: str,
        version: str,
        tarball: Path,
        metadata: dict,
        token: str,
    ) -> str:
        # Ensure the package entry exists before publishing a version
        await self.ensure_package_exists(name, metadata, token)

        async with httpx.AsyncClient(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0,
        ) as client:
            with tarball.open("rb") as f:
                resp = await client.post(
                    f"/packages/{name}/publish",
                    files={"tarball": (tarball.name, f, "application/gzip")},
                    data={
                        "version": version,
                        "description": metadata.get("description", ""),
                        "metadata": json.dumps(metadata),
                    },
                )
            self._raise_for_status(resp, name)
            return resp.json().get("url", f"https://ipkgs.com/packages/{name}")

    # Sync wrappers
    def get_package_sync(self, name: str) -> PackageMetadata:
        return asyncio.run(self.get_package(name))

    def search_sync(self, query: str, limit: int = 20, sort: str = "relevance") -> list[PackageMetadata]:
        return asyncio.run(self.search(query, limit, sort))
