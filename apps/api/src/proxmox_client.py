"""Minimal Proxmox API helper."""
from __future__ import annotations

from typing import Any, Dict, Optional

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from .config import NodeConfig


class ProxmoxClientError(RuntimeError):
    """Base exception for Proxmox client failures."""


class ProxmoxAuthError(ProxmoxClientError):
    """Raised when the API rejects our credentials."""


class ProxmoxClient:
    """Lightweight wrapper around the Proxmox REST API."""

    def __init__(self, node: NodeConfig) -> None:
        self._node = node
        if not node.verify_tls:
            self._verify: bool | str = False
            urllib3.disable_warnings(InsecureRequestWarning)
        elif node.ca_bundle:
            self._verify = node.ca_bundle
        else:
            self._verify = True
        self._api_root = f"https://{node.host}:{node.api_port}/api2/json"
        self._session = requests.Session()
        self._csrf_token: Optional[str] = None
        self._authenticated = False

    def _ensure_authenticated(self, force: bool = False) -> None:
        if force:
            self._authenticated = False
        if not self._authenticated:
            self._authenticate()

    def _authenticate(self) -> None:
        """Exchange username/password for a session ticket."""
        auth_url = f"{self._api_root}/access/ticket"
        try:
            response = self._session.post(
                auth_url,
                data={
                    "username": self._node.username,
                    "password": self._node.password,
                },
                verify=self._verify,
                timeout=10,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # type: ignore[attr-defined]
            status = exc.response.status_code if exc.response else None
            if status == 401:
                raise ProxmoxAuthError(
                    "Proxmox rejected the provided credentials or realm."
                ) from exc
            raise ProxmoxClientError("Unable to authenticate with Proxmox API.") from exc
        except requests.RequestException as exc:
            raise ProxmoxClientError("Unable to reach Proxmox API.") from exc

        data = response.json()["data"]
        self._session.cookies.set("PVEAuthCookie", data["ticket"])
        self._csrf_token = data.get("CSRFPreventionToken")
        self._authenticated = True

    def _request(self, path: str, method: str = "GET", **kwargs: Any) -> Dict[str, Any]:
        url = f"{self._api_root}{path}"
        headers = kwargs.pop("headers", {})
        if method.upper() != "GET" and self._csrf_token:
            headers.setdefault("CSRFPreventionToken", self._csrf_token)

        self._ensure_authenticated()

        for attempt in range(2):
            response = self._session.request(
                method=method,
                url=url,
                verify=self._verify,
                timeout=10,
                headers=headers,
                **kwargs,
            )

            if response.status_code == 401 and attempt == 0:
                # Ticket expired—refresh and retry once.
                self._ensure_authenticated(force=True)
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:  # type: ignore[attr-defined]
                status = exc.response.status_code if exc.response else None
                if status == 401:
                    raise ProxmoxAuthError(
                        "Authentication failed; verify credentials or API token."
                    ) from exc
                raise ProxmoxClientError(
                    f"Proxmox API responded with status {status or 'unknown'}."
                ) from exc
            except requests.RequestException as exc:
                raise ProxmoxClientError("Error communicating with Proxmox API.") from exc

            payload = response.json()
            return payload.get("data", payload)

        raise ProxmoxAuthError("Authentication failed after retrying Proxmox ticket exchange.")

    def status(self) -> Dict[str, Any]:
        """Return the node status payload."""
        return self._request(f"/nodes/{self._node.node_name}/status")
