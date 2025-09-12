"""
MCP policy enforcement for guardian tools.

Enhancements:
- Hot-reloadable policy.json loader.
- Audited allow/deny decisions via guardian.audit (delegates to centralized audit chain when available).
- Optional soft mode (MCP_POLICY_SOFT_MODE=1) logs violations but avoids raising, returning safe no-op values.
- Safer checks for file system roots, extensions, and HTTP schemes/hosts/ports when present in policy.

Backward-compatible API: fs_read(path), fs_write(path, content), http_get(url)
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.parse
from typing import Any, Dict, Optional

from . import audit as _audit


# -----------------
# Policy management
# -----------------
_POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.json")
_POLICY: Optional[Dict[str, Any]] = None
_POLICY_MTIME: float = 0.0


class MCPDenied(Exception):
    pass


def _load_policy(force: bool = False) -> Dict[str, Any]:
    global _POLICY, _POLICY_MTIME
    try:
        mtime = os.path.getmtime(_POLICY_PATH)
    except Exception:
        mtime = 0.0
    if force or _POLICY is None or mtime > _POLICY_MTIME:
        with open(_POLICY_PATH, encoding="utf-8") as f:
            _POLICY = json.load(f) or {}
        _POLICY_MTIME = mtime
    return _POLICY or {}


def _actor() -> str:
    return os.getenv("MCP_ACTOR", "system")


def _soft_mode() -> bool:
    return os.getenv("MCP_POLICY_SOFT_MODE", "0") == "1"


def _audit_decision(
    *,
    tool: str,
    decision: str,
    reason: str,
    target: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {"tool": tool, "decision": decision, "reason": reason, "target": target}
    if extra:
        payload.update(extra)
    try:
        _audit.append_event(
            actor=_actor(),
            action=f"mcp.{tool}.{decision}",
            ctx={"module": "guardian.mcp_policy"},
            payload=payload,
        )
    except Exception:
        # Audit should never block policy enforcement
        pass


def _get_tool_cfg(tool: str) -> Dict[str, Any]:
    pol = _load_policy()
    cfg = (pol.get("mcp_tools") or {}).get(tool)
    if not cfg:
        _audit_decision(
            tool=tool, decision="deny", reason="tool-not-allowed", target=tool
        )
        if _soft_mode():
            return {}
        raise MCPDenied(f"tool not allowed: {tool}")
    return cfg


def _allowed_path(tool: str, path: str) -> Dict[str, Any]:
    cfg = _get_tool_cfg(tool)
    p = pathlib.Path(path).resolve()
    roots = [pathlib.Path(r).resolve() for r in (cfg.get("paths") or [])]
    allowed = False
    for root in roots:
        try:
            p.relative_to(root)
            allowed = True
            break
        except Exception:
            continue
    if not allowed:
        _audit_decision(
            tool=tool,
            decision="deny",
            reason="path-not-permitted",
            target=str(p),
            extra={"roots": [str(r) for r in roots]},
        )
        if _soft_mode():
            return cfg
        raise MCPDenied(f"path not permitted: {p}")

    # Optional extension filter
    exts = cfg.get("extensions")
    if exts:
        ext = p.suffix.lower()
        if ext not in {e.lower() for e in exts}:
            _audit_decision(
                tool=tool,
                decision="deny",
                reason="extension-not-allowed",
                target=str(p),
                extra={"ext": ext},
            )
            if not _soft_mode():
                raise MCPDenied(f"extension not permitted: {ext}")

    return cfg


def fs_read(path: str) -> str:
    """Read a text file if within allowed roots and mode permits."""
    cfg = _allowed_path("fs.read", path)
    if cfg.get("mode") != "read":
        _audit_decision(
            tool="fs.read", decision="deny", reason="mode-violation", target=str(path)
        )
        if _soft_mode():
            return ""
        raise MCPDenied("mode violation")
    try:
        data = pathlib.Path(path).read_text(encoding="utf-8")
        _audit_decision(
            tool="fs.read",
            decision="allow",
            reason="ok",
            target=str(path),
            extra={"bytes": len(data.encode("utf-8"))},
        )
        return data
    except Exception as e:
        _audit_decision(
            tool="fs.read",
            decision="deny",
            reason="io-error",
            target=str(path),
            extra={"error": type(e).__name__},
        )
        if _soft_mode():
            return ""
        raise


def fs_write(path: str, content: str) -> bool:
    """Write text to a file if within allowed roots and mode permits."""
    cfg = _allowed_path("fs.write", path)
    if cfg.get("mode") != "write":
        _audit_decision(
            tool="fs.write", decision="deny", reason="mode-violation", target=str(path)
        )
        if _soft_mode():
            return False
        raise MCPDenied("mode violation")

    max_bytes = cfg.get("max_bytes")
    b = content.encode("utf-8")
    if isinstance(max_bytes, int) and len(b) > max_bytes:
        _audit_decision(
            tool="fs.write",
            decision="deny",
            reason="size-exceeded",
            target=str(path),
            extra={"bytes": len(b), "max": max_bytes},
        )
        if _soft_mode():
            return False
        raise MCPDenied(f"write exceeds max_bytes: {len(b)} > {max_bytes}")

    p = pathlib.Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        _audit_decision(
            tool="fs.write",
            decision="allow",
            reason="ok",
            target=str(path),
            extra={"bytes": len(b)},
        )
        return True
    except Exception as e:
        _audit_decision(
            tool="fs.write",
            decision="deny",
            reason="io-error",
            target=str(path),
            extra={"error": type(e).__name__},
        )
        if _soft_mode():
            return False
        raise


def http_get(url: str) -> Dict[str, Any]:
    """Policy-checked HTTP GET (preview only). No network IO is performed here."""
    cfg = _get_tool_cfg("http.get")
    u = urllib.parse.urlparse(url)
    host = (u.hostname or "").lower()
    scheme = (u.scheme or "").lower()
    port = u.port or (443 if scheme == "https" else 80 if scheme == "http" else None)

    allowed_hosts = {h.lower() for h in (cfg.get("hosts") or [])}
    if allowed_hosts and host not in allowed_hosts:
        _audit_decision(
            tool="http.get",
            decision="deny",
            reason="host-not-permitted",
            target=url,
            extra={"host": host},
        )
        if _soft_mode():
            return {
                "preview_only": True,
                "url": url,
                "allowed": False,
                "reason": "host-not-permitted",
            }
        raise MCPDenied(f"host not permitted: {host}")

    allowed_schemes = {s.lower() for s in (cfg.get("schemes") or [])}
    if allowed_schemes and scheme not in allowed_schemes:
        _audit_decision(
            tool="http.get",
            decision="deny",
            reason="scheme-not-permitted",
            target=url,
            extra={"scheme": scheme},
        )
        if _soft_mode():
            return {
                "preview_only": True,
                "url": url,
                "allowed": False,
                "reason": "scheme-not-permitted",
            }
        raise MCPDenied(f"scheme not permitted: {scheme}")

    allowed_ports = set(cfg.get("ports") or [])
    if allowed_ports and (port not in allowed_ports):
        _audit_decision(
            tool="http.get",
            decision="deny",
            reason="port-not-permitted",
            target=url,
            extra={"port": port},
        )
        if _soft_mode():
            return {
                "preview_only": True,
                "url": url,
                "allowed": False,
                "reason": "port-not-permitted",
            }
        raise MCPDenied(f"port not permitted: {port}")

    # SAFE preview only; do not perform actual network calls here
    _audit_decision(
        tool="http.get",
        decision="allow",
        reason="ok",
        target=url,
        extra={"host": host, "scheme": scheme, "port": port},
    )
    return {"preview_only": True, "url": url, "allowed": True}


__all__ = [
    "MCPDenied",
    "fs_read",
    "fs_write",
    "http_get",
]
