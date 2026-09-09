from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mcp_server import McpServer
from app.services.crypto import decrypt_json


def _headers(server: McpServer) -> dict[str, str]:
    extra = decrypt_json(server.headers_enc)
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def _http_rpc(server: McpServer, method: str, params: dict | None = None) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    response = httpx.post(server.url, json=payload, headers=_headers(server), timeout=45)
    if response.status_code >= 400:
        return {"ok": False, "error": f"MCP HTTP {response.status_code}: {response.text[:400]}"}
    text = response.text
    if "data:" in text and text.strip().startswith("event:") or "\ndata:" in text:
        for line in text.splitlines():
            if line.startswith("data:"):
                text = line[5:].strip()
                break
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"MCP returned non-JSON: {text[:300]}"}
    if body.get("error"):
        return {"ok": False, "error": body["error"]}
    return {"ok": True, "result": body.get("result")}


def _stdio_rpc(server: McpServer, method: str, params: dict | None = None) -> dict[str, Any]:
    if not server.command:
        return {"ok": False, "error": "stdio MCP server has no command"}
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    try:
        proc = subprocess.run(
            [server.command, *(server.args or [])],
            input=payload + "\n",
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    line = next((ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")), "")
    if not line:
        return {"ok": False, "error": proc.stderr[:400] or "No JSON from MCP stdio process"}
    body = json.loads(line)
    if body.get("error"):
        return {"ok": False, "error": body["error"]}
    return {"ok": True, "result": body.get("result")}


def call_mcp(server: McpServer, method: str, params: dict | None = None) -> dict[str, Any]:
    if server.transport in ("http", "sse"):
        return _http_rpc(server, method, params)
    if server.transport == "stdio":
        return _stdio_rpc(server, method, params)
    return {"ok": False, "error": f"Unknown MCP transport {server.transport}"}


def list_brand_mcp(db: Session, brand_id: UUID) -> list[McpServer]:
    return list(
        db.scalars(
            select(McpServer).where(McpServer.brand_id == brand_id, McpServer.enabled.is_(True))
        ).all()
    )


def list_tools(db: Session, brand_id: UUID) -> dict[str, Any]:
    servers = list_brand_mcp(db, brand_id)
    out = []
    for server in servers:
        call_mcp(
            server,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sweety", "version": "0.1.0"},
            },
        )
        listed = call_mcp(server, "tools/list", {})
        out.append(
            {
                "server_id": str(server.id),
                "name": server.name,
                "transport": server.transport,
                "tools": (listed.get("result") or {}).get("tools") if listed.get("ok") else [],
                "error": listed.get("error"),
            }
        )
    return {"ok": True, "servers": out}


def call_tool(db: Session, brand_id: UUID, server_id: str, tool: str, arguments: dict | None = None) -> dict[str, Any]:
    server = db.get(McpServer, server_id)
    if server is None or server.brand_id != brand_id:
        return {"ok": False, "error": "MCP server not found"}
    return call_mcp(server, "tools/call", {"name": tool, "arguments": arguments or {}})
