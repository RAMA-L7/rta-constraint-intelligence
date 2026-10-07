"""
Ṛta — MCP access control and audit trail.

The MCP server is a *local* stdio process, so "access control" here is not a
network perimeter — it is a **capability boundary** so that an assistant wired
to the tool cannot do more than the operator intended. The same code path also
produces the audit trail, so "what did the agent run, and with what argument
shapes?" is answerable after the fact.

Roles (deny by default — a tool that appears in no role is allowed for nobody):

| Role | Capability |
|---|---|
| ``reader`` (default) | the 8 deterministic engine tools + sources health + local docs search |
| ``engineer`` | reader + GitHub issue search + store queries + the ``rta_investigate`` composite |
| ``maintainer`` | engineer + ``rta_source_store_record`` (the only mutating tool) |

Configuration:

* ``RTA_MCP_ROLE`` — ``reader`` | ``engineer`` | ``maintainer``. Unset or
  unrecognised falls back to ``reader`` (never to a higher role).
* ``RTA_MCP_ALLOW_MUTATIONS`` — must be ``1``/``true``/``yes`` for the
  maintainer role to be able to write. Mutations stay off by default even for
  ``maintainer``.

Auditing records a SHA-256 **digest** of the arguments, the argument key names,
the outcome, the duration and which sources were consulted. Argument *values*
are never written — the audit log must not become a second, undeclared copy of
a customer's constraint files.
"""

from __future__ import annotations

import os
import time
from typing import Optional

ROLE_READER = "reader"
ROLE_ENGINEER = "engineer"
ROLE_MAINTAINER = "maintainer"

#: Ascending capability order.
ROLE_ORDER = (ROLE_READER, ROLE_ENGINEER, ROLE_MAINTAINER)

#: The frozen deterministic engine tools — available to every role.
ENGINE_TOOLS = (
    "rta_analyze",
    "rta_lint",
    "rta_convert",
    "rta_generate",
    "rta_snapshot",
    "rta_diff",
    "rta_corners",
    "rta_rules",
)

#: Diagnostics + local, credential-free knowledge.
READER_TOOLS = ENGINE_TOOLS + (
    "rta_sources_health",
    "rta_source_docs_search",
)

#: Sources that consume a credential or reach the network, plus the composite.
ENGINEER_TOOLS = READER_TOOLS + (
    "rta_source_issues_search",
    "rta_source_store_query",
    "rta_investigate",
)

#: The only mutating tool in the server.
MAINTAINER_TOOLS = ENGINEER_TOOLS + (
    "rta_source_store_record",
)

ROLE_TOOLS = {
    ROLE_READER: frozenset(READER_TOOLS),
    ROLE_ENGINEER: frozenset(ENGINEER_TOOLS),
    ROLE_MAINTAINER: frozenset(MAINTAINER_TOOLS),
}

#: Tools that must additionally pass the mutations switch.
MUTATING_TOOLS = frozenset({"rta_source_store_record"})

_TRUE = ("1", "true", "yes", "on")


def resolve_role(env: Optional[dict] = None) -> str:
    """Resolve the configured role. Unknown or unset → ``reader``."""
    source = os.environ if env is None else env
    raw = str(source.get("RTA_MCP_ROLE", "")).strip().lower()
    return raw if raw in ROLE_TOOLS else ROLE_READER


def role_is_explicit(env: Optional[dict] = None) -> bool:
    """True when ``RTA_MCP_ROLE`` named a role this module recognises."""
    source = os.environ if env is None else env
    raw = str(source.get("RTA_MCP_ROLE", "")).strip().lower()
    return raw in ROLE_TOOLS


def mutations_allowed(env: Optional[dict] = None) -> bool:
    """Mutations are opt-in and off by default."""
    source = os.environ if env is None else env
    return str(source.get("RTA_MCP_ALLOW_MUTATIONS", "")).strip().lower() in _TRUE


def allowed_tools(role: str) -> frozenset:
    return ROLE_TOOLS.get(role, ROLE_TOOLS[ROLE_READER])


def known_tool(tool: str) -> bool:
    """True when at least one role is granted this tool."""
    return any(tool in tools for tools in ROLE_TOOLS.values())


def check(role: str, tool: str, env: Optional[dict] = None) -> dict:
    """Decide whether ``role`` may call ``tool``.

    Returns a decision dict — ``{"allowed": bool, "role": str, "tool": str,
    "reason": str|None, "required_role": str|None}``. Deny-by-default applies to
    unknown tools as well as to known tools the role lacks.
    """
    effective = role if role in ROLE_TOOLS else ROLE_READER

    if not known_tool(tool):
        return {"allowed": False, "role": effective, "tool": tool,
                "reason": "DENY_UNKNOWN_TOOL", "required_role": None}

    if tool in MUTATING_TOOLS and not mutations_allowed(env):
        return {"allowed": False, "role": effective, "tool": tool,
                "reason": "DENY_MUTATIONS_DISABLED",
                "required_role": ROLE_MAINTAINER}

    if tool in allowed_tools(effective):
        return {"allowed": True, "role": effective, "tool": tool,
                "reason": None, "required_role": None}

    for candidate in ROLE_ORDER:
        if tool in allowed_tools(candidate):
            return {"allowed": False, "role": effective, "tool": tool,
                    "reason": "DENY_ROLE_LACKS_TOOL",
                    "required_role": candidate}

    return {"allowed": False, "role": effective, "tool": tool,
            "reason": "DENY_UNKNOWN_TOOL", "required_role": None}


def describe_role(role: str) -> dict:
    """Human-readable summary used by ``rta_sources_health`` diagnostics."""
    effective = role if role in ROLE_TOOLS else ROLE_READER
    return {
        "role": effective,
        "explicit": role_is_explicit(),
        "tools": sorted(allowed_tools(effective)),
        "tool_count": len(allowed_tools(effective)),
        "mutations_allowed": mutations_allowed(),
        "mutating_tools": sorted(MUTATING_TOOLS),
    }


def role_matrix() -> dict:
    """Full role → tools map. Used by docs and by the access tests."""
    roles = {role: sorted(allowed_tools(role)) for role in ROLE_ORDER}
    denied_everywhere = sorted(
        tool for tool in (ENGINE_TOOLS + READER_TOOLS + ENGINEER_TOOLS
                          + MAINTAINER_TOOLS)
        if not known_tool(tool))
    return {"roles": roles, "denied_for_all_roles": denied_everywhere,
            "mutating_tools": sorted(MUTATING_TOOLS),
            "default_role": ROLE_READER}


def audit(tool: str, role: str, args: Optional[dict], outcome: str,
          started_at: Optional[float] = None, degraded: bool = False,
          sources_used: Optional[list] = None,
          store=None) -> None:
    """Append an audit row. Best-effort — failure to audit never fails a call."""
    duration_ms = 0.0
    if isinstance(started_at, (int, float)):
        duration_ms = round((time.monotonic() - float(started_at)) * 1000.0, 3)
    writer = store
    if writer is None:
        try:
            from rta.sources import get_sources
            writer = get_sources().get("store")
        except Exception:                            # noqa: BLE001 - best effort
            writer = None
    if writer is None:
        return
    try:
        writer.audit(tool=tool, role=role, args=args, outcome=outcome,
                     duration_ms=duration_ms, degraded=degraded,
                     sources_used=sources_used)
    except Exception:                                # noqa: BLE001 - best effort
        return
