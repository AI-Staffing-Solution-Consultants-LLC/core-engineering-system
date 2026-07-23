from dataclasses import dataclass


@dataclass
class BoardLogEntry:
    action: str
    result: str
    reasoning_ref: str
    timestamp: str


@dataclass
class AuditFinding:
    severity: str
    reason: str
    evidence: dict
