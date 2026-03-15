"""Registry HTTP client."""

from __future__ import annotations

import asyncio
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

DEFAULT_REGISTRY = "https://api.ipkgs.com/v1"

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class RegistryClient:
    def __init__(self, base_url: str = DEFAULT_REGISTRY, token: str | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _make_transport(self) -> httpx.AsyncHTTPTransport:
        return httpx.AsyncHTTPTransport(retries=3)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers(),
            transport=self._make_transport(),
            timeout=30.0,
        )

    def _raise_for_status(self, resp: httpx.Response, package_name: str = "") -> None:
        if resp.status_code == 404:
            raise PackageNotFoundError(package_name)
        if resp.status_code in (401, 403):
            raise AuthenticationError("Authentication failed. Run `ipkgs login`.")
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
            resp = await client.get(f"/packages/{name}/versions/{version}")
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
                "/packages",
                params={"q": query, "limit": limit, "sort": sort},
            )
            self._raise_for_status(resp)
            return [PackageMetadata.model_validate(p) for p in resp.json().get("packages", [])]

    async def download_tarball(
        self,
        url: str,
        dest: Path,
        on_chunk: Callable[[int], None],
    ) -> None:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        on_chunk(len(chunk))

    async def publish(
        self,
        name: str,
        version: str,
        tarball: Path,
        metadata: dict,
        token: str,
    ) -> str:
        async with httpx.AsyncClient(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0,
        ) as client:
            with tarball.open("rb") as f:
                resp = await client.post(
                    f"/packages/{name}/versions/{version}",
                    files={"tarball": (tarball.name, f, "application/gzip")},
                    data={"metadata": str(metadata)},
                )
            self._raise_for_status(resp, name)
            return resp.json().get("url", f"{self._base}/packages/{name}")

    # Sync wrappers for use from Click commands
    def get_package_sync(self, name: str) -> PackageMetadata:
        return asyncio.run(self.get_package(name))

    def search_sync(self, query: str, limit: int = 20, sort: str = "relevance") -> list[PackageMetadata]:
        return asyncio.run(self.search(query, limit, sort))
