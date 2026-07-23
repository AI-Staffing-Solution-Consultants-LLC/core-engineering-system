from dataclasses import dataclass


@dataclass
class LedgerEntry:
    type: str
    timestamp: str
    data: dict
    prev_hash: str
    chain_hash: str
