"""Authentication and credential management."""

from __future__ import annotations

import os

import httpx
import keyring

from ipkgs.exceptions import AuthenticationError

SERVICE_NAME = "ipkgs"


class AuthManager:
    def __init__(self, registry_url: str) -> None:
        self._registry = registry_url.rstrip("/")

    def get_token(self) -> str | None:
        """Read token from keyring, fallback to IPKGS_TOKEN env var."""
        env_token = os.environ.get("IPKGS_TOKEN")
        if env_token:
            return env_token
        return keyring.get_password(SERVICE_NAME, self._registry)

    def set_token(self, token: str) -> None:
        keyring.set_password(SERVICE_NAME, self._registry, token)

    def clear_token(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, self._registry)
        except keyring.errors.PasswordDeleteError:
            pass

    async def login(self, username: str, password: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._registry}/auth/token",
                json={"username": username, "password": password},
            )
            if resp.status_code in (401, 403):
                raise AuthenticationError("Invalid username or password.")
            if resp.status_code >= 400:
                raise AuthenticationError(f"Login failed: {resp.text}")
            token: str = resp.json()["token"]
            self.set_token(token)
            return token
