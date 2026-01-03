"""Entry point for the Flask application."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable

from werkzeug.exceptions import HTTPException

from flask import (
    Flask,
    jsonify,
    abort,
    url_for,
    request,
    Response,
)

from .config import ConfigError, load_app_config, NodeConfig
from .proxmox_client import (
    ProxmoxAuthError,
    ProxmoxClient,
    ProxmoxClientError,
)
from .wol import wake


def create_app() -> Flask:
    """Application factory so the app can run locally or under gunicorn."""
    app = Flask(__name__)
    try:
        app_config = load_app_config()
    except ConfigError as exc:  # pragma: no cover - startup validation
        raise RuntimeError(str(exc)) from exc

    clients: dict[str, ProxmoxClient] = {}
    default_node_id = app_config.list_nodes()[0].id

    def _client_for(node_id: str) -> tuple[NodeConfig, ProxmoxClient]:
        try:
            node = app_config.get_node(node_id)
        except KeyError as exc:
            abort(404, description=str(exc))

        client = clients.get(node_id)
        if client is None:
            client = ProxmoxClient(node)
            clients[node_id] = client
        return node, client

    def _fetch_status(node_id: str) -> dict[str, Any]:
        node, client = _client_for(node_id)
        snapshot: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
            "meta": node.public_dict(),
            "payload": None,
            "error": None,
        }
        try:
            snapshot["payload"] = client.status()
        except ProxmoxAuthError as exc:
            snapshot["error"] = {"message": str(exc), "code": 401}
        except ProxmoxClientError as exc:
            snapshot["error"] = {"message": str(exc), "code": 502}
        return snapshot

    def _format_duration(seconds: Any) -> str:
        if seconds in (None, ""):
            return "—"
        try:
            total_seconds = int(float(seconds))
        except (TypeError, ValueError):
            return "—"
        delta = timedelta(seconds=total_seconds)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")
        return " ".join(parts)

    def _format_bytes(value: Any) -> str:
        if value in (None, ""):
            return "—"
        try:
            num = float(value)
        except (TypeError, ValueError):
            return "—"
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        idx = 0
        while num >= 1024 and idx < len(units) - 1:
            num /= 1024
            idx += 1
        return f"{num:.1f} {units[idx]}"

    def _format_load(values: Any) -> str:
        if not values:
            return "—"
        if isinstance(values, str):
            parts = values.split()
        elif isinstance(values, Iterable):
            parts = list(values)
        else:
            parts = [values]
        parts = [str(p) for p in parts][:3]
        return " / ".join(parts) if parts else "—"

    def _state_variant(status: str | None, error: dict[str, Any] | None) -> tuple[str, str]:
        if error:
            return "Error", "error"
        label = (status or "Unknown").title()
        normalized = (status or "").lower()
        if normalized in {"online", "running", "up"}:
            return label, "ok"
        if normalized in {"unknown", "maintenance"}:
            return label, "warn"
        return label, "error"

    def _build_snapshot(node_id: str) -> dict[str, Any]:
        snapshot = _fetch_status(node_id)
        payload = snapshot.get("payload") or {}
        error = snapshot.get("error")
        label, variant = _state_variant(payload.get("status"), error)
        memory_info = payload.get("memory") or {}
        mem_used = memory_info.get("used")
        mem_total = memory_info.get("total")
        mem_percent = None
        if mem_used and mem_total:
            try:
                mem_percent = round(float(mem_used) / float(mem_total) * 100, 1)
            except ZeroDivisionError:
                mem_percent = None
        cpu_percent = None
        cpu_value = payload.get("cpu")
        if cpu_value is not None:
            try:
                cpu_percent = round(float(cpu_value) * 100, 1)
            except (TypeError, ValueError):
                cpu_percent = None
        guests = {
            "kvm": payload.get("kvm") or 0,
            "lxc": payload.get("lxc") or 0,
        }
        guests["total"] = (guests["kvm"] or 0) + (guests["lxc"] or 0)

        snapshot["state"] = {
            "label": label,
            "variant": variant,
            "online": not error,
        }
        snapshot["metrics"] = {
            "uptime": _format_duration(payload.get("uptime")),
            "cpu_percent": cpu_percent,
            "memory_percent": mem_percent,
            "memory_summary": (
                f"{_format_bytes(mem_used)} / {_format_bytes(mem_total)}"
                if mem_total
                else "—"
            ),
            "load": _format_load(payload.get("loadavg")),
            "guests": guests,
        }
        snapshot["checked_at"] = datetime.utcnow()
        return snapshot

    def _serialize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": snapshot["id"],
            "name": snapshot["name"],
            "meta": snapshot["meta"],
            "state": snapshot["state"],
            "metrics": snapshot["metrics"],
            "error": snapshot["error"],
            "checked_at": snapshot.get("checked_at") and snapshot["checked_at"].isoformat(),
        }

    def _derive_events(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for node in nodes:
            stamp = node.get("checked_at")
            clock = None
            if stamp:
                try:
                    clock = datetime.fromisoformat(stamp).strftime("%H:%M:%S")
                except ValueError:
                    clock = stamp
            base = {
                "node": node["name"],
                "timestamp": stamp,
                "clock": clock,
            }
            error = node.get("error")
            if error:
                events.append(
                    {
                        **base,
                        "tone": "danger",
                        "title": f"{node['name']} unreachable",
                        "body": error.get("message", "Authentication or API error."),
                    }
                )
                continue

            state = node.get("state", {})
            if not state.get("online"):
                events.append(
                    {
                        **base,
                        "tone": "warn",
                        "title": f"{node['name']} offline",
                        "body": "Wake the node or investigate connectivity.",
                    }
                )

            metrics = node.get("metrics", {})
            cpu_percent = metrics.get("cpu_percent")
            if isinstance(cpu_percent, (int, float)) and cpu_percent >= 80:
                events.append(
                    {
                        **base,
                        "tone": "info",
                        "title": f"{node['name']} sustained load",
                        "body": f"CPU at {cpu_percent:.1f}% over the last sample.",
                    }
                )

            guests = (metrics.get("guests") or {}).get("total")
            if guests == 0:
                events.append(
                    {
                        **base,
                        "tone": "info",
                        "title": f"{node['name']} idle",
                        "body": "No guests scheduled on this host.",
                    }
                )

        if not events:
            stamp = datetime.utcnow()
            events.append(
                {
                    "tone": "info",
                    "title": "All systems nominal",
                    "body": "No alerts detected during the last sync window.",
                    "timestamp": stamp.isoformat(),
                    "clock": stamp.strftime("%H:%M:%S"),
                }
            )
        return events[:6]

    def _gather_dashboard_state():
        snapshots = [_build_snapshot(node.id) for node in app_config.list_nodes()]
        serialized = [_serialize_snapshot(snapshot) for snapshot in snapshots]
        events = _derive_events(serialized)
        generated_at = datetime.utcnow()
        payload = {
            "generated_at": generated_at.isoformat(),
            "nodes": serialized,
            "events": events,
        }
        return snapshots, payload, generated_at

    def _status_payload(node_id: str):
        snapshot = _fetch_status(node_id)
        error = snapshot.get("error")
        if error:
            body = {"error": error["message"], "node": node_id}
            return jsonify(body), error["code"]
        return jsonify({"node": snapshot["meta"], "status": snapshot["payload"]})

    @app.get("/")
    def index():
        """Return API metadata and discovery links."""
        return jsonify(
            {
                "name": "Command & Control API",
                "version": "1.0.0",
                "docs_url": url_for("docs", _external=True),
                "openapi_url": url_for("openapi_spec", _external=True),
            }
        )

    @app.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok"})

    @app.get("/api/nodes")
    def list_nodes():
        nodes = [node.public_dict() for node in app_config.list_nodes()]
        return jsonify(nodes)

    @app.get("/api/dashboard")
    def dashboard_snapshot_api():
        _, payload, _ = _gather_dashboard_state()
        return jsonify(payload)

    @app.get("/api/nodes/<string:node_id>/status")
    def node_status(node_id: str):
        return _status_payload(node_id)

    @app.get("/api/node/status")
    def default_node_status():
        """Backward compatible endpoint hitting the first configured node."""
        return _status_payload(default_node_id)

    @app.post("/api/nodes/<string:node_id>/wake")
    def node_wake(node_id: str) -> tuple[Response, int]:
        node, _ = _client_for(node_id)
        wake(node.mac_address)
        return jsonify({"message": f"Magic packet sent for {node_id}"}), 202

    @app.post("/api/node/wake")
    def default_node_wake() -> tuple[Response, int]:
        wake(app_config.get_node(default_node_id).mac_address)
        return jsonify({"message": f"Magic packet sent for {default_node_id}"}), 202

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        payload = {
            "error": {
                "code": error.code,
                "name": error.name,
                "message": error.description,
            }
        }
        return jsonify(payload), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception) -> tuple[Response, int]:
        app.logger.exception("Unhandled exception during request")
        payload = {
            "error": {
                "code": 500,
                "name": "Internal Server Error",
                "message": "Unexpected server error.",
            }
        }
        return jsonify(payload), 500

    OPENAPI_TEMPLATE: Dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Command & Control API",
            "version": "1.0.0",
            "description": "Fleet telemetry, health, and Wake-on-LAN controls for Proxmox nodes.",
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Service liveness",
                    "responses": {
                        "200": {
                            "description": "API is reachable",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Health"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/nodes": {
                "get": {
                    "summary": "List configured nodes",
                    "responses": {
                        "200": {
                            "description": "Node inventory",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/NodeMetadata"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/dashboard": {
                "get": {
                    "summary": "Cluster snapshot",
                    "responses": {
                        "200": {
                            "description": "Aggregated telemetry and derived events",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Dashboard"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/nodes/{node_id}/status": {
                "get": {
                    "summary": "Fetch live telemetry for a node",
                    "parameters": [
                        {
                            "name": "node_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Node payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/NodeStatus"}
                                }
                            },
                        },
                        "404": {"description": "Node not found"},
                    },
                }
            },
            "/api/node/status": {
                "get": {
                    "summary": "Fetch telemetry for the default node",
                    "responses": {
                        "200": {
                            "description": "Node payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/NodeStatus"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/nodes/{node_id}/wake": {
                "post": {
                    "summary": "Send a wake-on-LAN packet to a node",
                    "parameters": [
                        {
                            "name": "node_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "202": {
                            "description": "Wake dispatched",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/WakeResponse"}
                                }
                            },
                        },
                        "404": {"description": "Node not found"},
                    },
                }
            },
            "/api/node/wake": {
                "post": {
                    "summary": "Wake the default node",
                    "responses": {
                        "202": {
                            "description": "Wake dispatched",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/WakeResponse"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Health": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "ok"}
                    },
                },
                "NodeMetadata": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "host": {"type": "string"},
                        "api_port": {"type": "integer"},
                        "node_name": {"type": "string"},
                        "mac_address": {"type": "string"},
                    },
                    "required": ["id", "name", "host", "api_port", "node_name"],
                    "additionalProperties": True,
                },
                "NodeStatus": {
                    "type": "object",
                    "properties": {
                        "node": {"$ref": "#/components/schemas/NodeMetadata"},
                        "status": {
                            "type": "object",
                            "description": "Raw Proxmox status payload",
                        },
                        "error": {
                            "type": "string",
                            "nullable": True,
                        },
                    },
                },
                "Event": {
                    "type": "object",
                    "properties": {
                        "tone": {"type": "string", "enum": ["info", "warn", "danger"]},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "clock": {"type": "string"},
                    },
                },
                "Snapshot": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "meta": {"$ref": "#/components/schemas/NodeMetadata"},
                        "state": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "variant": {"type": "string"},
                                "online": {"type": "boolean"},
                            },
                        },
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "uptime": {"type": "string"},
                                "cpu_percent": {"type": "number", "nullable": True},
                                "memory_percent": {"type": "number", "nullable": True},
                                "memory_summary": {"type": "string"},
                                "load": {"type": "string"},
                                "guests": {
                                    "type": "object",
                                    "properties": {
                                        "kvm": {"type": "integer"},
                                        "lxc": {"type": "integer"},
                                        "total": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "error": {
                            "type": "object",
                            "nullable": True,
                        },
                        "checked_at": {"type": "string", "format": "date-time"},
                    },
                },
                "Dashboard": {
                    "type": "object",
                    "properties": {
                        "generated_at": {"type": "string", "format": "date-time"},
                        "nodes": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Snapshot"},
                        },
                        "events": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Event"},
                        },
                    },
                },
                "WakeResponse": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                },
            }
        },
    }

    @app.get("/openapi.json")
    def openapi_spec():
        spec = deepcopy(OPENAPI_TEMPLATE)
        spec["servers"] = [{"url": request.url_root.rstrip("/")}]
        return jsonify(spec)

    @app.get("/docs")
    def docs():
        html = f"""
        <!doctype html>
        <html lang=\"en\">
          <head>
            <meta charset=\"utf-8\" />
            <title>Command & Control API Docs</title>
            <style>body {{ margin: 0; padding: 0; }}</style>
          </head>
          <body>
            <redoc spec-url=\"{url_for('openapi_spec')}\"></redoc>
            <script src=\"https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js\"></script>
          </body>
        </html>
        """
        return Response(html, mimetype="text/html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
