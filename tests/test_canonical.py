"""
Unit and property tests for canonical serialization.
"""

import json

import pytest

from python.canonical import (
    canonical_json_bytes,
    compute_content_hash,
    deserialize_record_stream,
    serialize_record_stream,
)


def test_canonical_json_key_sorting():
    obj1 = {"b": 2, "a": 1, "c": 3}
    obj2 = {"c": 3, "b": 2, "a": 1}
    assert canonical_json_bytes(obj1) == canonical_json_bytes(obj2)
    assert canonical_json_bytes(obj1) == b'{"a":1,"b":2,"c":3}'


def test_canonical_json_no_whitespace():
    obj = {"items": [1, 2, 3], "nested": {"key": "val"}}
    b = canonical_json_bytes(obj)
    assert b" " not in b
    assert b"\n" not in b
    assert b"\t" not in b


def test_stream_serialization_roundtrip():
    records = [
        {"epoch": 1, "loss": 2.45},
        {"epoch": 2, "loss": 1.82},
        {"epoch": 3, "loss": 0.95},
    ]
    stream = serialize_record_stream(records)
    unpacked = deserialize_record_stream(stream)
    assert len(unpacked) == len(records)
    for orig, raw in zip(records, unpacked):
        assert json.loads(raw.decode("utf-8")) == orig


def test_content_hash_deterministic():
    records = [{"step": 10}, {"step": 20}]
    s1 = serialize_record_stream(records)
    s2 = serialize_record_stream(records)
    assert compute_content_hash(s1) == compute_content_hash(s2)
    assert len(compute_content_hash(s1)) == 32


def test_truncated_stream_raises():
    stream = b"\x00\x00\x00\x10hello"  # Declares 16 bytes but only provides 5
    with pytest.raises(ValueError, match="Truncated record"):
        deserialize_record_stream(stream)
