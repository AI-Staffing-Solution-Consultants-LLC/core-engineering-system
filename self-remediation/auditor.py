"""
Auditor Agent — co-located with self-remediation service (port 8087).

Provides audit trail validation for board log entries and VCP (Verified Change
Procedure) entries. Report-only architecture — never blocks execution based on
findings. Uses MemoryPlugin for context retrieval.

Endpoints:
  POST /audit/check   — validate board log against MemoryPlugin context
  POST /audit/report  — generate and persist an audit finding
  GET  /audit/findings — list all persisted audit findings

Core functions:
  validate_board_log(log_entry, memory_context) → AuditFinding | None
  check_vcp(vcp_entry) → AuditFinding | None
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

# ── Known-valid tool prefixes (auditor's reference allowlist) ──────────

_KNOWN_VALID_TOOLS = frozenset(
    {
        "kubectl get pods",
        "kubectl get nodes",
        "kubectl logs",
        "kubectl describe",
        "kubectl top",
        "git status",
        "git log",
        "git diff",
        "docker ps",
        "docker logs",
    }
)

# ── Shell metacharacter blocklist ──────────────────────────────────────

_METACHARACTERS = ("|", ";", "&", "$(", "`", ">", "<", "${", "&&", "||")


# ── Data model ─────────────────────────────────────────────────────────


@dataclass
class AuditFinding:
    """A single audit finding — report-only, never blocks execution."""

    id: str
    timestamp: str
    finding_type: str  # "allowlist_violation", "context_mismatch", "vcp_invalid"
    severity: str  # "low", "medium", "high", "critical"
    board_entry_ref: Optional[str] = None
    vcp_entry: Optional[dict] = None
    description: str = ""
    match: Optional[dict] = None


# ── Core validation functions ──────────────────────────────────────────


def _tool_is_valid(tool: str) -> bool:
    """Check whether a tool command is in the known-valid set."""
    if not tool:
        return False
    for valid in _KNOWN_VALID_TOOLS:
        if tool == valid or tool.startswith(valid + " "):
            return True
    return False


def _contains_metacharacter(tool: str) -> bool:
    """Check whether a tool command contains shell metacharacters."""
    return any(mc in tool for mc in _METACHARACTERS)


def validate_board_log(log_entry: dict, memory_context: dict) -> Optional[AuditFinding]:
    """Validate a board log entry against known-valid tools and memory context.

    Args:
        log_entry: The board log entry with keys: tool, args, reasoning_log_ref, timestamp.
        memory_context: Context from MemoryPlugin with results list.

    Returns:
        AuditFinding if validation fails, None if the entry is clean.
    """
    tool = log_entry.get("tool", "")
    now_ts = datetime.now(timezone.utc).isoformat()

    # Gate 1: Metacharacter check — highest severity
    if _contains_metacharacter(tool):
        return AuditFinding(
            id=str(uuid.uuid4()),
            timestamp=now_ts,
            finding_type="allowlist_violation",
            severity="critical",
            board_entry_ref=log_entry.get("reasoning_log_ref"),
            description=(
                f"Board log tool command contains prohibited shell metacharacter: "
                f"'{tool}' — this is a potential injection vector."
            ),
        )

    # Gate 2: Known-valid tool check
    if not _tool_is_valid(tool):
        return AuditFinding(
            id=str(uuid.uuid4()),
            timestamp=now_ts,
            finding_type="allowlist_violation",
            severity="critical",
            board_entry_ref=log_entry.get("reasoning_log_ref"),
            description=(
                f"Board log tool command is not in the known-valid allowlist: "
                f"'{tool}' — execution may be unsafe."
            ),
        )

    # Gate 3: Context check — does the tool contradict memory context restrictions?
    context_results = memory_context.get("results", [])
    for ctx in context_results:
        content = ctx.get("content", "").lower()
        tool_lower = tool.lower()
        # If context says a tool is restricted/requires-approval and the log uses it
        if ("restricted" in content or "requires human approval" in content) and any(
            word in tool_lower for word in content.split() if len(word) > 3
        ):
            return AuditFinding(
                id=str(uuid.uuid4()),
                timestamp=now_ts,
                finding_type="context_mismatch",
                severity="high",
                board_entry_ref=log_entry.get("reasoning_log_ref"),
                description=(
                    f"Board log tool '{tool}' may violate memory context restriction: "
                    f"'{ctx.get('content', '')}'"
                ),
                match=ctx,
            )

    # Gate 4: If context has specific allowlist entries, check tool against them
    has_context_allowlist = any(
        "allowed" in ctx.get("content", "").lower() for ctx in context_results
    )
    if has_context_allowlist and not _tool_is_valid(tool):
        return AuditFinding(
            id=str(uuid.uuid4()),
            timestamp=now_ts,
            finding_type="allowlist_violation",
            severity="high",
            board_entry_ref=log_entry.get("reasoning_log_ref"),
            description=(
                f"Board log tool '{tool}' not found in context-provided allowlist"
            ),
        )

    return None


def check_vcp(vcp_entry: dict) -> Optional[AuditFinding]:
    """Validate a VCP (Verified Change Procedure) entry for required fields.

    Required fields: vcp_id, action, target, namespace, requested_by, approved_by.

    Args:
        vcp_entry: The VCP entry to validate.

    Returns:
        AuditFinding if validation fails, None if the entry is valid.
    """
    now_ts = datetime.now(timezone.utc).isoformat()

    required_fields = [
        "vcp_id",
        "action",
        "target",
        "namespace",
        "requested_by",
        "approved_by",
    ]

    for field in required_fields:
        value = vcp_entry.get(field)
        if not value:
            return AuditFinding(
                id=str(uuid.uuid4()),
                timestamp=now_ts,
                finding_type="vcp_invalid",
                severity="high",
                vcp_entry=vcp_entry,
                description=(
                    f"VCP entry is missing required field '{field}' — "
                    f"change procedure is incomplete and cannot be verified."
                ),
            )

    return None


# ── In-memory findings store ───────────────────────────────────────────

_findings: list[AuditFinding] = []


def _add_finding(finding: AuditFinding) -> AuditFinding:
    """Persist an audit finding to the in-memory store."""
    _findings.append(finding)
    return finding


def _get_findings() -> list[AuditFinding]:
    """Retrieve all persisted audit findings."""
    return list(_findings)
