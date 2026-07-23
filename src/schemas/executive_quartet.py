from dataclasses import dataclass


@dataclass
class ExecutiveQuartetMember:
    name: str
    port: int
    personality: str
    memory_context: str

    def __post_init__(self):
        if not self.name:
            raise ValueError("name must not be empty")
        if not (1024 <= self.port <= 65535):
            raise ValueError("port must be between 1024 and 65535")
