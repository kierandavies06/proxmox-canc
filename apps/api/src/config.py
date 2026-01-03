"""Application configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from a local .env file if present.
load_dotenv(Path.cwd() / ".env")


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or parsed."""


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


@dataclass(frozen=True)
class NodeConfig:
    """Settings necessary to talk to a single Proxmox node."""

    id: str
    name: str
    host: str
    api_port: int
    username: str
    password: str
    node_name: str
    mac_address: str
    verify_tls: bool
    ca_bundle: str | None

    def public_dict(self) -> Dict[str, Any]:
        """Return a redacted view safe to expose via the API."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "api_port": self.api_port,
            "node_name": self.node_name,
            "verify_tls": self.verify_tls,
        }


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration state."""

    nodes: Dict[str, NodeConfig]

    def get_node(self, node_id: str) -> NodeConfig:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown node id '{node_id}'") from exc

    def list_nodes(self) -> list[NodeConfig]:
        return list(self.nodes.values())


def load_app_config() -> AppConfig:
    """Load the node list from the configured JSON file."""
    config_path = Path(os.getenv("NODE_CONFIG_PATH", "nodes.json"))
    if not config_path.exists():
        raise ConfigError(
            f"Node config file '{config_path}' not found. Set NODE_CONFIG_PATH or create nodes.json."
        )

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc}") from exc

    entries = raw.get("nodes", [])
    if not entries:
        raise ConfigError("Node config must include at least one entry under 'nodes'.")

    nodes: Dict[str, NodeConfig] = {}
    for entry in entries:
        try:
            node = NodeConfig(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                host=entry["host"],
                api_port=int(entry.get("api_port", 8006)),
                username=entry["username"],
                password=entry["password"],
                node_name=entry["node_name"],
                mac_address=entry["mac_address"],
                verify_tls=_bool(entry.get("verify_tls", True), True),
                ca_bundle=entry.get("ca_bundle") or None,
            )
        except KeyError as exc:
            raise ConfigError(
                f"Missing required field '{exc.args[0]}' in node entry {entry}"
            ) from exc

        if node.id in nodes:
            raise ConfigError(f"Duplicate node id '{node.id}' detected in {config_path}.")

        nodes[node.id] = node

    return AppConfig(nodes=nodes)
