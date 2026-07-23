from dataclasses import dataclass, field


@dataclass
class MemoryPluginRequest:
    operation: str
    context: str
    entity: str
    payload: dict


@dataclass
class MemoryPluginResponse:
    success: bool
    data: dict
    error: str = ""
