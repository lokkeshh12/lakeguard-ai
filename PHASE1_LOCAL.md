# Phase 1: Local metadata control plane

This increment introduces a SQLite-backed adapter (`lakeguard/control.py`) with pipeline registry, execution audit, committed watermarks, and incident events. It is designed for **local testing**, not as a production multi-worker control plane.

## Windows setup

From the repository root in PowerShell:

```powershell
python -m pip install -e ".[dev]"
python -m ruff check lakeguard agents tests
python -m pytest -q
```

## Interactive demonstration

```python
from lakeguard.control import ControlStore
store = ControlStore("local_state/control.db")
store.register("orders", {"source": "local_json"})
run_id = store.start("orders")
# Only call succeed after the corresponding data write has completed.
store.succeed(run_id, row_count=3, watermark="2026-11-12T00:00:00Z")
print(store.watermark("orders"))
```

## Design boundaries

- The local adapter does not yet execute PySpark jobs or verify Delta commit IDs.
- SQLite audit/watermark transactions are atomic **with each other**, but not with a separate Delta data write. The production design requires idempotent writes and replay/reconciliation after a crash between data commit and metadata commit.
- Watermark strings must use a normalized fixed-format UTC representation for lexical ordering; future iterations should validate and parse timestamps.
- No concurrent-run lease or stale-run recovery is implemented. Do not use this adapter for parallel production scheduling.
- Next increments: Pydantic pipeline models, pluggable metadata storage, Delta ingestion integration, quality-rule registry, and crash recovery tests.
