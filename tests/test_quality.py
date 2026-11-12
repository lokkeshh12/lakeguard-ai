"""Fast, deterministic quality unit tests."""
from lakeguard.quality import detect_null_spike, detect_schema_change, detect_volume_drop

def test_volume_drop():
    assert detect_volume_drop(40, 100).kind == "volume_drop"
    assert detect_volume_drop(90, 100) is None
    assert detect_volume_drop(0, 0) is None

def test_null_spike():
    assert detect_null_spike(10, 100).kind == "null_spike"
    assert detect_null_spike(1, 100) is None

def test_schema_change():
    assert detect_schema_change({"a", "c"}, {"a", "b"}) == {"missing": ["b"], "unexpected": ["c"]}
