from dataclasses import dataclass, field


@dataclass(frozen=True)
class CryptoContext:
    service: str
    collection: str
    field_name: str
    route: str | None = None
    document_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
