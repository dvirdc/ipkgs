"""Authentication and credential management."""

from __future__ import annotations

import asyncio
import os
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import keyring

SERVICE_NAME = "ipkgs"
CALLBACK_PORT = 9876
CALLBACK_HOST = "localhost"


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

    async def login_browser(self, provider: str = "github") -> str:
        """
        Full OAuth browser login flow:
          1. GET /auth/login?provider=<provider>&cli_callback=http://localhost:9876/callback
          2. Open returned URL in browser
          3. Receive access_token at local callback server
          4. POST /auth/token to exchange for ipkgs_ API token
          5. Store in keyring and return token
        """
        callback_url = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}/callback"

        # Step 1 — fetch the OAuth redirect URL from the registry
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._registry}/auth/login",
                params={"provider": provider, "cli_callback": callback_url},
            )
            resp.raise_for_status()
            auth_url: str = resp.json()["url"]

        # Step 2 — start local callback server, open browser
        access_token = await _run_callback_server(auth_url)

        # Step 4 — exchange access_token for ipkgs_ API token
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._registry}/auth/token",
                json={"access_token": access_token},
            )
            resp.raise_for_status()
            api_token: str = resp.json()["token"]

        # Step 5 — persist
        self.set_token(api_token)
        return api_token


async def _run_callback_server(auth_url: str) -> str:
    """
    Spin up a one-shot HTTP server on localhost:9876, open the browser,
    and wait for the OAuth callback with ?access_token=...
    Returns the access_token string.
    """
    received: dict[str, str] = {}
    ready = threading.Event()
    done = threading.Event()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            token = params.get("access_token", [None])[0]
            error = params.get("error", [None])[0]

            if token:
                received["access_token"] = token
                body = b"<html><body><h2>Authenticated! You can close this tab.</h2></body></html>"
                self.send_response(200)
            else:
                received["error"] = error or "unknown"
                body = b"<html><body><h2>Authentication failed. You can close this tab.</h2></body></html>"
                self.send_response(400)

            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

        def log_message(self, *args: object) -> None:
            pass  # suppress request logs

    server = HTTPServer((CALLBACK_HOST, CALLBACK_PORT), _Handler)

    def _serve() -> None:
        ready.set()
        server.handle_request()  # handle exactly one request then exit
        server.server_close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    ready.wait()

    # Step 3 — open browser
    webbrowser.open(auth_url)

    # Wait for callback (up to 120 seconds)
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: done.wait(timeout=120)
    )

    if "error" in received:
        raise RuntimeError(f"OAuth error: {received['error']}")
    if "access_token" not in received:
        raise TimeoutError("Timed out waiting for browser authentication.")

    return received["access_token"]
