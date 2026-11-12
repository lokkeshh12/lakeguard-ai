"""Incident records and stable idempotency keys."""
from dataclasses import dataclass, field
from hashlib import sha256
from datetime import datetime, timezone

@dataclass
class Incident:
    """Serializable evidence for a pipeline reliability incident."""
    pipeline: str
    run_id: str
    signal: str
    evidence: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def incident_id(self) -> str:
        """Stable ID prevents repeated actions on duplicate alerts."""
        return sha256(f"{self.pipeline}|{self.run_id}|{self.signal}".encode()).hexdigest()[:24]
