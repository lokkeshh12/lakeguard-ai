"""Typed configuration and fully qualified identifier validation."""

import re

from pydantic import BaseModel, Field, field_validator

_IDENTIFIER = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$"
)


class PipelineConfig(BaseModel):
    """Validated configuration for a single ingestion pipeline."""

    source_path: str
    schema_location: str
    checkpoint: str
    bronze_table: str
    silver_table: str
    quarantine_table: str
    gold_table: str
    primary_key: str = "order_id"
    sequence_column: str = "event_ts"
    required_columns: list[str] = Field(default_factory=list)
    max_null_rate: float = Field(default=0.05, ge=0, le=1)
    min_volume_ratio: float = Field(default=0.6, ge=0, le=1)

    @field_validator("bronze_table", "silver_table", "quarantine_table", "gold_table")
    @classmethod
    def valid_table(cls, value: str) -> str:
        """Reject SQL injection via table identifiers."""
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("Expected catalog.schema.table identifier")
        return value
