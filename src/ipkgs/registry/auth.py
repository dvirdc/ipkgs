"""Authentication and credential management."""

from __future__ import annotations

import os

import keyring

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
